from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import math
import os
import json
import random
import time
from collections import defaultdict, deque

from tqdm import tqdm
from data_collect.component_collector.variater.variation_waterfall_types import GenCodeParams, ProjectInfo, EvolCodeParams, StageNPipelineParams, StageOnePipelineParams
from utils.llm import MAX_LENGTH_EXCEEDED_ERROR, SUCCESS_CODE, llm_chat
import re
import subprocess

from data_collect.component_collector.variater.prompts_waterfall_with_init_code import DEVELOPMENT_PLAN_PROMPT, GEN_CODE_SNIPPET_PROMPT_ITER, SPA_INFER_PROMPT, DOUBLE_CHECK_PROMPT


class ComponentGraph:
    def __init__(self):
        self.graph = defaultdict(list)

    def add_dependency(self, child, parent):
        self.graph[child].append(parent)

    def get_all_parents(self, component):
        visited = set()
        queue = deque([component])
        parents = []

        while queue:
            current = queue.popleft()
            if current not in visited:
                visited.add(current)
                parents.append(current)
                for parent in self.graph[current]:
                    if parent not in visited:
                        queue.append(parent)

        return parents[1:]


def kill_variations():
    process = subprocess.Popen(
        ["bash", "kill_variations.sh"], stdout=subprocess.PIPE, text=True)
    print('done kill variations')


class ComponentVariation:
    def __init__(self, assistant):
        self._assistant = assistant

    def postprocess_code_response(self, content):
        if not content:
            return None

        # if there is </s> in the end of the content, remove it
        content = content.rstrip('</s>')

        pattern = r"```(.*?)\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)

        if matches:
            # Extract the code from each match
            return matches[0][1]
        pattern2 = r"'''(.*?)\n(.*?)'''"
        matches2 = re.findall(pattern2, content, re.DOTALL)
        if matches2:
            # Extract the code from each match
            return matches2[0][1]

        # remove \n at the end first
        content = content.strip()
        if content.startswith('```'):
            content = content[3:]
        if content.startswith("'''"):
            content = content[3:]
        # check whether there is ``` in the end
        if content.endswith('```'):
            content = content[:-3]
        if content.endswith("'''"):
            content = content[:-3]

        # remove the single line at the beginning if it is a language label
        if content.startswith('javascript\n'):
            content = content[11:]
        elif content.startswith('typescript\n'):
            content = content[11:]
        elif content.startswith('css\n'):
            content = content[4:]
        elif content.startswith('scss\n'):
            content = content[5:]
        elif content.startswith('sass\n'):
            content = content[5:]
        elif content.startswith('less\n'):
            content = content[5:]
        elif content.startswith('jsx\n'):
            content = content[4:]
        elif content.startswith('tsx\n'):
            content = content[4:]
        return content

    def chat(self, prompt, temperature=0.1):
        print('/// chatting...')
        print(prompt)
        print('------------------- done prompt')

        response = self._assistant.chat(prompt, temp=temperature)
        if response['error_code'] != SUCCESS_CODE:
            if response['error_code'] == MAX_LENGTH_EXCEEDED_ERROR:
                print('TOO LONG, breaking...')
                return None
            print('Error in generating response, breaking...')
            return None

        result = response['content']

        max_continue = 10
        continue_count = 0
        while True:
            if response['output_token_len'] >= 4095:
                print('gen not done, continue')
                chat_hist = [
                    {'role': 'user', 'content': prompt},
                    {'role': 'assistant', 'content': response['content']}
                ]
                response = self._assistant.chat(
                    'continue', chat_hist, temperature)
                print('--- current output len: ', response['output_token_len'])
                if response['error_code'] != SUCCESS_CODE:
                    if response['error_code'] == MAX_LENGTH_EXCEEDED_ERROR:
                        print('TOO LONG, breaking...')
                        return result
                    print('Error in generating response, breaking...')
                    return result
                result += response['content']
                print('--- current result: ', result)
                continue_count += 1
                if continue_count >= max_continue:
                    print('--- done generate all')
                    break
            else:
                print('--- done generate all')
                break

        return result

    def extract_repo_comp_names(self, screenshot_path):
        repo_comp_record = {}
        for file in os.listdir(screenshot_path):
            # split by the last dot and get the file name and type
            file_name, file_type = file.rsplit('.', 1)
            if file_type == 'png':
                repo_name, comp_name = file_name.rsplit('-_-_-', 1)
                if repo_name not in repo_comp_record:
                    repo_comp_record[repo_name] = set()
                repo_comp_record[repo_name].add(comp_name)

        result_list = []
        for repo, comp_set in repo_comp_record.items():
            result_list.append({
                'repo': repo,
                'comps': list(comp_set)
            })
        return result_list

    def extract_comp_name(self, code):
        match = re.search(
            r'export\s+default\s+(?:class\s+|function\s+)?(\w+)|\b(\w+)\s*=\s*React\.memo\(|\b(\w+)\s*=\s*forwardRef\(|\b(\w+)\s*=\s*connect\(', code)
        if match:
            return match.group(1) or match.group(2) or match.group(3) or match.group(4)
        return None

    def is_component_used(self, content, component_name):
        pattern = re.compile(rf'<{component_name}(?:\s+[^>]*)?\s*/?>')
        return bool(pattern.search(content))

    def load_comp_and_label_depth(self, repo_path, comps):
        print('')
        print('-- repo_path:', repo_path)
        comp_data_record = []
        graph = ComponentGraph()
        for comp in comps:
            comp_path = os.path.join(repo_path, f'{comp}_bundled.json')

            # check if the component path exists
            if not os.path.exists(comp_path):
                print('---- comp_path does not exist:', comp_path)
                continue

            # load json
            with open(comp_path, 'r') as f:
                comp_data = json.load(f)
                comp_data['comp_name_in_file'] = comp
                comp_code = comp_data['code_with_ori_img'] if 'code_with_ori_img' in comp_data else comp_data['debug_component']
                comp_name = self.extract_comp_name(comp_code)
                comp_data['export_comp_name'] = comp_name
                comp_data_record.append(comp_data)

        for comp_data in comp_data_record:
            comp_name = comp_data['export_comp_name']
            for parent_comp in comp_data_record:
                parent_name = parent_comp['export_comp_name']
                parent_code = parent_comp['code_with_ori_img'] if 'code_with_ori_img' in parent_comp else parent_comp['debug_component']
                if comp_name != parent_name and self.is_component_used(parent_code, comp_name):
                    graph.add_dependency(comp_name, parent_name)

        print('graph:', graph.graph)

        max_depth = 0
        all_parents = []
        for comp_data in comp_data_record:
            comp_data['parents'] = graph.get_all_parents(
                comp_data['export_comp_name'])
            all_parents.extend(comp_data['parents'])
            if len(comp_data['parents']) > max_depth:
                max_depth = len(comp_data['parents'])

        # sort based on the number of parents
        comp_data_record = sorted(
            comp_data_record, key=lambda x: len(x['parents']))

        return comp_data_record, list(set(all_parents)), max_depth

    def load_processed_components(self, variation_output_path):
        """
        Scan the variation_output_path for completed component variations.
        Each variation filename is expected to follow the format:
        {component_name}_waterfall_{system_purpose_inference_idx}_{iter_num}_{task_idx}-{total_task_num}.json

        We will:
        - Parse these filenames
        - Track progress of each component in terms of completed tasks.
        - Determine which components are fully processed.
        - Return a set of fully processed component names.
        """
        filename_pattern = re.compile(
            r'^(?P<component>.+)_waterfall_(?P<system_idx>\d+)_(?P<iter_num>\d+)_(?P<task_idx>\d+)-(?P<total_task_num>\d+)\.json$'
        )

        component_tasks = {}

        # Scan all JSON files in the directory
        for fname in os.listdir(variation_output_path):
            if fname.endswith('.json'):
                match = filename_pattern.match(fname)
                if match:
                    comp = match.group('component')
                    task_idx = int(match.group('task_idx'))
                    total_task_num = int(match.group('total_task_num'))

                    if comp not in component_tasks:
                        component_tasks[comp] = {
                            'total': total_task_num,
                            'tasks_completed': set()
                        }

                    component_tasks[comp]['tasks_completed'].add(task_idx)

        # Determine which components are fully completed
        fully_processed_components = set()
        for comp, info in component_tasks.items():
            # Check if tasks_completed count == total_task_num
            if len(info['tasks_completed']) == info['total']:
                # All tasks completed
                fully_processed_components.add(comp)
            else:
                # Incomplete: we do not add to fully_processed_components
                # If you wanted to remove partial files, you could do so here,
                # but usually you'd just not consider them processed.
                pass

        return fully_processed_components

    def preprocess_components(self, repo_comp_list, variation_output_path):
        """
        Given a list of repos with their components, and the variation output path:
        1. Determine which components are fully processed from previous runs.
        2. Filter out the repo_comp_list so that only components that are not fully processed remain.
        """
        fully_processed_components = self.load_processed_components(
            variation_output_path)

        # Filter the repo_comp_list so that we only keep components not fully processed
        filtered_repo_comp_list = []
        for repo_item in repo_comp_list:
            repo = repo_item['repo']
            comps = repo_item['comps']

            # Keep only components not in the fully_processed_components set
            new_comps = [
                c for c in comps if c not in fully_processed_components]

            if new_comps:
                filtered_repo_comp_list.append({
                    'repo': repo,
                    'comps': new_comps
                })
        print('Before filtering:', len(repo_comp_list),
              'After filtering:', len(filtered_repo_comp_list))
        return filtered_repo_comp_list

    def fetch_repo_and_comp(self, repo_dir, repo_comp_list, variation_output_dir, iter_num):
        comp_count = 0
        for repo_comp in tqdm(repo_comp_list, desc='repo variation'):
            repo = repo_comp['repo']
            repo_path = os.path.join(repo_dir, repo)

            # create the repo folder in the variation output path and copy the package.json and pkg_candidate.json
            variation_output_path = os.path.join(variation_output_dir, repo)
            if not os.path.exists(variation_output_path):
                os.makedirs(variation_output_path)
            variation_files = os.listdir(variation_output_path)

            # load all components and label the depth of the component
            comp_data_record, all_parents, max_depth = self.load_comp_and_label_depth(
                repo_path, repo_comp['comps'])

            all_sys_infers = []

            for comp_data in comp_data_record:
                print('------ Processing comp: ', comp_data['comp_name_in_file'],
                      ', parents: ', comp_data['parents'])

                # not used by other components
                if len(comp_data['parents']) == 0 and not comp_data['export_comp_name'] in all_parents:
                    print(
                        f'comp: {comp_data["comp_name_in_file"]} is not used by other components')
                    continue

                comp_count += 1

                variation_file_prefix = f'{comp_data["comp_name_in_file"]}_waterfall_'
                processed = False
                for file in variation_files:
                    if file.startswith(variation_file_prefix):
                        print('---- variation file exists:', file,
                              comp_data["comp_name_in_file"])
                        processed = True
                        break

                if processed:
                    continue

                style = comp_data['filtered_css'] if 'filtered_css' in comp_data else comp_data['raw_css']
                comp_code = comp_data['code_with_ori_img'] if 'code_with_ori_img' in comp_data else comp_data['debug_component']

                infer_num = min(math.floor(
                    len(comp_data['parents']) / max_depth / 0.333) + 1, 3) if max_depth > 0 else 1

                evol_start_time = time.time()
                self.evol_code(EvolCodeParams(
                    style=style,
                    code=comp_code,
                    infer_num=infer_num,
                    infer_history=all_sys_infers,
                    iter_num=iter_num,
                    source_component_name=comp_data['comp_name_in_file'],
                    source_component_data=copy.deepcopy(comp_data),
                    output_path=variation_output_path))
                evol_end_time = time.time()
                print('!! evol_time:', evol_end_time - evol_start_time)

    def postprocess_dev_plan(self, dev_plan):
        dev_plan_json = json.loads(dev_plan)
        result = []
        for task_idx, task in enumerate(dev_plan_json):
            tmp_result = f'Task {task_idx + 1}'
            if 'title' in task:
                tmp_result += f': {task["title"]}\n'
            if 'objective' in task:
                tmp_result += f'Objective: {task["objective"]}\n'
            if 'components_logic' in task:
                tmp_result += f'Components Logic: {task["components_logic"]}\n'
            if 'builds_on' in task:
                tmp_result += f'Builds On: {task["builds_on"]}\n'
            if 'best_practices' in task:
                tmp_result += f'Best Practices: {task["best_practices"]}\n'
            result.append(tmp_result)
        return result

    def format_code_snippet(self, style, comp_code):
        return f'Component Code:\n{comp_code}\n\nStyle:\n{style}\n'

    def postprocess_infered_systems(self, infered_systems):
        infered_systems = self.postprocess_code_response(infered_systems)
        infered_systems_json = json.loads(infered_systems)
        result = []
        for system in infered_systems_json:
            tmp_result = ''
            if 'name' in system:
                tmp_result += f'System Name: {system["name"]}\n'
            if 'category' in system:
                tmp_result += f'Category: {system["category"]}\n'
            if 'purpose' in system:
                tmp_result += f'Purpose: {system["purpose"]}\n'
            if 'code_snippet_usage' in system:
                tmp_result += f'Code Snippet Usage: {system["code_snippet_usage"]}\n'
            if 'complexity' in system:
                tmp_result += f'Complexity: {system["complexity"]}\n'
            if 'features' in system:
                tmp_result += f'Features: {system["features"]}\n'
            result.append(tmp_result)
        return result

    def save_code(self, code, path):
        with open(path, 'w') as f:
            f.write(code)

    def gen_code(self, params: GenCodeParams):
        iter_num = params.iter_num
        dev_plan_list = params.dev_plan_list
        system_purpose_inference = params.system_purpose_inference
        project_info = params.project_info
        source_component_name = params.source_component_name
        source_component_data = params.source_component_data
        system_purpose_inference_idx = params.system_purpose_inference_idx
        output_path = params.output_path

        current_code_snippet = params.code_snippet
        for task_idx, task in enumerate(dev_plan_list):
            tmp_prompt = GEN_CODE_SNIPPET_PROMPT_ITER.format(
                system_description=system_purpose_inference,
                current_implementation=current_code_snippet,
                next_task_description=f'Task {task_idx + 1}: {task}',
            )

            tmp_code_snippet = self.chat(tmp_prompt, 0.1)
            if not tmp_code_snippet:
                return None

            double_check_prompt = DOUBLE_CHECK_PROMPT.format(
                code_snippet=tmp_code_snippet)
            double_check_response = self.chat(double_check_prompt, 0.0)
            if not double_check_response:
                return None
            if 'passed' in double_check_response.lower():
                print('double check passed')
            else:
                print('double check failed')
                print('### original code snippet:')
                print(tmp_code_snippet)
                print('### new code snippet:')
                print(double_check_response)
                tmp_code_snippet = double_check_response

            print(
                f'\n iter {iter_num} step 6. code_snippet {task_idx} ***********************************************************')
            print(task)
            print('------')
            print(tmp_prompt)
            print('------')
            print(tmp_code_snippet)
            current_code_snippet = tmp_code_snippet

            # postprocess the code snippet
            comp_code = self.postprocess_code_response(
                current_code_snippet)

            print(
                f'\n iter {iter_num} step 7. saving code {task_idx} ***********************************************************')
            print(comp_code)
            project_info['code'] = comp_code
            source_component_data['filtered_css'] = ''
            source_component_data['code_with_ori_img'] = comp_code
            source_component_data['system_requirement'] = system_purpose_inference
            source_component_data['iter_num'] = 0
            source_component_data['task_idx'] = task_idx
            source_component_data['total_task_num'] = len(dev_plan_list)
            source_component_data['task_description'] = task
            variation_path = os.path.join(
                output_path, f'{source_component_name}_waterfall_{system_purpose_inference_idx}_{iter_num}_{task_idx}-{len(dev_plan_list)}.json')
            with open(variation_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(source_component_data, indent=4))
        return project_info

    def stage_one_pipeline(self, params: StageOnePipelineParams):
        code_snippet = params.code_snippet
        system_purpose_inference_idx = params.system_purpose_inference_idx
        system_purpose_inference = params.system_purpose_inference
        source_component_name = params.source_component_name
        source_component_data = params.source_component_data
        output_path = params.output_path

        project_info: ProjectInfo = {
            'system_purpose': system_purpose_inference,
            'requirements': '',
            'layout': '',
            'tech_plan': '',
            'dev_plan': '',
            'style': '',
            'code': ''
        }

        # step 5: generate development plan
        dev_plan = self.chat(
            DEVELOPMENT_PLAN_PROMPT.format(system_description=system_purpose_inference, code_snippet=code_snippet), 0.3)
        if not dev_plan:
            return None
        dev_plan = self.postprocess_code_response(dev_plan)
        project_info['dev_plan'] = dev_plan
        print(
            '\nstep 2. dev_plan ***********************************************************')
        print(dev_plan)
        dev_plan_splited = self.postprocess_dev_plan(dev_plan)
        print(dev_plan_splited)

        # # step 6: generate code
        project_info = self.gen_code(GenCodeParams(
            iter_num=0,
            code_snippet=code_snippet,
            dev_plan_list=dev_plan_splited,
            start_code_snippet='',
            system_purpose_inference=system_purpose_inference,
            requirements='',
            layouts='',
            tech_architecture='',
            dev_plan=dev_plan,
            project_info=project_info,
            system_purpose_inference_idx=system_purpose_inference_idx,
            output_path=output_path,
            source_component_name=source_component_name,
            source_component_data=source_component_data
        ))

        return project_info

    def evol_code(self, params: EvolCodeParams):
        style = params.style
        comp_code = params.code
        infer_num = params.infer_num
        infer_history = params.infer_history
        iter_num = params.iter_num
        comp_data_copy = params.source_component_data
        comp = params.source_component_name
        variation_output_path = params.output_path

        print('*'*100)
        print('evolving...')

        code_snippet = self.format_code_snippet(style, comp_code)
        process_log = []

        # step 1: inference the system or application based on the given code snippet
        infered_systems = self.chat(
            SPA_INFER_PROMPT.format(
                infer_num=infer_num,
                example_systems='\n'.join(infer_history) if len(
                    infer_history) > 0 else '<NO EXAMPLES YET>',
                code_snippet=code_snippet,
            ), 0.9)
        if not infered_systems:
            return None
        infered_systems = self.postprocess_infered_systems(infered_systems)
        print('\nstep 1. infered_requirements ***********************************************************')
        print('target infer num: ', infer_num)
        print('infered history: ', infer_history)
        for infer_system in infered_systems:
            print('------')
            print(infer_system)  # print the infered system
            print('------')
            infer_history.append(infer_system)

        def process_system(sys_idx, isystem):
            iter_count = 0

            project_info: ProjectInfo = {
                'system_purpose': '',
                'requirements': '',
                'layout': '',
                'tech_plan': '',
                'dev_plan': '',
                'style': '',
                'code': ''
            }
            project_info = self.stage_one_pipeline(StageOnePipelineParams(
                code_snippet=code_snippet,
                system_purpose_inference_idx=sys_idx,
                system_purpose_inference=isystem,
                source_component_name=comp,
                source_component_data=comp_data_copy,
                output_path=variation_output_path
            ))

            return project_info
        process_system(0, infered_systems[0])


def parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--iter_num', type=int, default=3)
    parser.add_argument('--screenshot_path', type=str)
    parser.add_argument('--repo_path', type=str)
    parser.add_argument('--variation_path', type=str)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()

    screenshot_path = args.screenshot_path
    repo_path = args.repo_path
    variation_path = args.variation_path

    assistant = llm_chat
    cv = ComponentVariation(assistant)
    repo_comp_counts = cv.extract_repo_comp_names(screenshot_path)
    repo_comp_counts = cv.preprocess_components(
        repo_comp_counts, variation_path)
    cv.fetch_repo_and_comp(
        repo_path, repo_comp_counts, variation_path, args.iter_num)
    print('Done')
