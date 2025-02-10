import json
import re
from threading import Lock
import traceback
import concurrent.futures
import os
import subprocess
from utils.util import postprocess_code_reponse
from utils.llm import llm_chat
from tqdm import tqdm
import networkx as nx
import argparse


class Distiller():
    def __init__(self, base_path, repo_path, output_dir, statistic, lock):
        self._base_path = base_path
        self._repo_path = os.path.normpath(repo_path)
        self._statistic = statistic
        self._lock = lock
        self._output_dir = os.path.join(
            output_dir, os.path.basename(self._repo_path))
        if not os.path.exists(self._output_dir):
            os.makedirs(self._output_dir)
        self._dependency_graph = None
        self._processed_files = {}

    def update_statistic(self, key, value):
        with self._lock:
            # If the key doesn't exist in the dictionary, initialize it with the incoming value
            if key not in self._statistic:
                self._statistic[key] = value
            else:
                # If the existing value is a list, append the new value if it is also a list, or extend if the new value is an item
                if isinstance(self._statistic[key], list):
                    if isinstance(value, list):
                        self._statistic[key].extend(value)
                    else:
                        self._statistic[key].append(value)
                # If the existing value is a number, add the new value to it
                elif isinstance(self._statistic[key], (int, float)):
                    self._statistic[key] += value

    def add_statistic(self, key, value):
        with self._lock:
            if key not in self._statistic:
                self._statistic[key] = value
            self._statistic[key] += value

    def rule_based_react_identification(self, file_content):
        # Enhanced and more specific patterns to better identify React components
        patterns = [
            # Class components
            r'class\s+\w+\s+extends\s+(React\.Component|Component)\b',
            r'import\s+React\b',  # Import React statement
            # Import specific from React (destructuring)
            r'import\s+\{[^}]*\}\s+from\s+[\'"]react[\'"]',
            r'React\.createElement\b',  # Explicit React createElement usage
            # Function component (capitalized functions)
            r'function\s+[A-Z]\w*\s*\(',
            # Arrow function components with explicit return
            r'const\s+[A-Z]\w*\s*=\s*\([^)]*\)\s*=>',
            # Return in a function that likely returns JSX
            r'return\s*\([^\)]',
            # File extensions for React components (optional heuristic)
            r'(\.jsx|\.tsx)\b',
            r'\/>\s*$',  # Closing JSX tag check at the end of the line
            r'<\w+\s*\/>',  # Self-closing JSX tag
            # Hooks usage
            r'(useState|useEffect|useContext|useReducer|useMemo|useCallback)\(',
            r'\bPropTypes\b',  # Usage of PropTypes
            r'<\w+',  # JSX element start
            r'<\/\w+>',  # JSX closing tag
            # Using Material-UI (common in React projects)
            r'from\s+[\'"]@material-ui/core',
        ]

        # Enhance readability and maintenance by separating JSX checks into a clear pattern
        jsx_patterns = [
            r'<\w+[^>]*>',  # Generic JSX opening tag
            r'<\w+.*?>.*?<\/\w+>',  # JSX with closing tag
        ]

        # Check both general React and JSX specific patterns
        react_checks = any(re.search(pattern, file_content,
                                     re.MULTILINE | re.DOTALL) for pattern in patterns)
        jsx_checks = any(re.search(pattern, file_content,
                                   re.MULTILINE | re.DOTALL) for pattern in jsx_patterns)

        return react_checks or jsx_checks

    def llm_based_react_identification(self, file_content):
        prompt = 'You will be given a code snippet. You need to check if it is implemented with React or not. You need to return a boolean value, true if it is a React component, false otherwise. For example, if the component is defined as follows: function MyComponent() { return <div>test</div>; }, then the output should be: true. REPLY WITH the boolean value only, no explanations, comments, or any other text needed. Here is the code snippet: '
        is_react_component = llm_chat.chat(
            prompt + file_content)
        if is_react_component is None:
            return True
        result = postprocess_code_reponse(is_react_component['content']).lower()
        return True if result == 'true' else False

    def is_react_component(self, file_content, use_llm):
        rule_based_result = self.rule_based_react_identification(file_content)
        print(f'--- rule_based_result: {rule_based_result}')
        if not use_llm:
            return rule_based_result
        if rule_based_result:
            llm_based_result = self.llm_based_react_identification(
                file_content)
            print(
                f'--- judge is react, rule_based_result: {rule_based_result}, llm_based_result: {llm_based_result}')
            return llm_based_result
        return False

    def find_all_files(self):
        # the file can not be under the node_modules, and must be under the src folder
        all_files = []
        for root, dirs, files in os.walk(self._repo_path):
            for file in files:
                if 'node_modules' in root:
                    continue
                if file.endswith(('.js', '.jsx', '.ts', '.tsx')):
                    path = os.path.join(root, file)
                    all_files.append(path)

                    # statistics
                    if file.endswith('.js'):
                        self.add_statistic('total_js_files', 1)
                    elif file.endswith('.jsx'):
                        self.add_statistic('total_jsx_files', 1)
                    elif file.endswith('.ts'):
                        self.add_statistic('total_ts_files', 1)
                    elif file.endswith('.tsx'):
                        self.add_statistic('total_tsx_files', 1)
        self.add_statistic('total_files', len(all_files))
        return all_files

    def find_react_components(self, use_llm=True):
        component_files = set()
        for root, dirs, files in os.walk(self._repo_path):
            for file in files:
                if 'node_modules' in root:
                    continue
                if file.endswith(('.js', '.jsx', '.ts', '.tsx')):
                    path = os.path.join(root, file)
                    try:
                        if not os.path.exists(path):
                            continue
                        with open(path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if self.is_react_component(content, use_llm):
                                # print(f"Found React component: {path}")
                                # component_files.append(path)
                                component_files.add(path)
                            # else:
                            #     print(f"Not a React component: {path}")
                    except Exception as e:
                        print(f"Error reading file {path}: {e}")
                        pass
        # statistics
        component_files = list(component_files)
        self.add_statistic('total_component_files', len(component_files))
        print(
            f"Total React component files in {self._repo_path}: {len(component_files)}")
        return component_files

    def find_imports(self, file_path):
        try:
            # Call the Node.js script passing the file path
            # print(f"Extracting imports from {file_path}")
            # print(f"Node.js script path: {os.path.join(self._base_path, 'js_parser.js')}")
            result = subprocess.run(
                ['node', os.path.join(self._base_path, 'js_parser.js'), file_path], capture_output=True, text=True)
            if result.stderr:
                print(f"Error running Node.js script: {result.stderr}")
                return []
            if result.stdout:
                # print(f"Output received from Node.js script: {result.stdout}")
                imports = json.loads(result.stdout)
                return imports
            else:
                print("No output received from Node.js script.")
                return []
        except Exception as e:
            print(f"Failed to extract imports: {e}")
            return []

    def resolve_import_path(self, current_file_path, import_statement, import_statement_str=None):
        try:
            if hasattr(import_statement, 'source') and hasattr(import_statement.source, 'value'):
                module_name = import_statement.source.value
            elif 'source' in import_statement and 'value' in import_statement['source']:
                module_name = import_statement['source']['value']
            else:
                return import_statement_str, False

            if module_name.startswith('.'):
                directory_of_current_file = os.path.dirname(current_file_path)
                resolved_path = os.path.join(
                    directory_of_current_file, module_name)

                if not os.path.splitext(resolved_path)[1]:
                    resolved_path += '.js'
                if not resolved_path.endswith(('.js', '.jsx', '.ts', '.tsx', '.css', '.scss', '.sass', '.less', '.styl')):
                    return import_statement_str, False
                return os.path.normpath(resolved_path), True
            else:
                return import_statement_str, False

        except AttributeError as e:
            return import_statement_str, False

    def recursive_imports(self, current_file_path, visited=None):
        if not current_file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
            return set()
        if visited is None:
            visited = set()

        if current_file_path in visited:
            return set()
        visited.add(current_file_path)

        imports = self.find_imports(current_file_path)
        print(f'imports for {current_file_path}: {len(imports)}')
        all_files = {current_file_path}

        for imp in imports:
            imp_path, is_local = self.resolve_import_path(
                current_file_path, imp)
            if imp_path and os.path.exists(imp_path) and not 'node_modules' in imp_path and 'src' in imp_path:
                all_files.update(self.recursive_imports(imp_path, visited))

        return all_files

    def find_css_imports(self, file_content):
        regex_css_path = r"import\s+.*?from\s+['\"]([^'\"]+\.css)['\"]|import\s+['\"]([^'\"]+\.css)['\"]"
        css_imports = re.findall(regex_css_path, file_content)
        css_paths = [
            path for sublist in css_imports for path in sublist if path]

        regex_whole_line = r"^.*import\s+.*?from\s+['\"].*?\.css['\"].*$|^.*import\s+['\"].*?\.css['\"].*$"
        file_content = re.sub(regex_whole_line, '',
                              file_content, flags=re.MULTILINE)
        return css_paths, file_content

    def distill_style_and_code(self, files):
        component_content = {}
        css_content = ""
        processed_css_files = set()  # Set to track processed CSS files

        for file_path in files:
            print(f'--- extracting file: {file_path} ---')
            if file_path in self._processed_files.keys():
                print(
                    f"loading already processed file {file_path} from output directory")
                with open(self._processed_files[file_path], 'r') as file:
                    processed_file_info = json.load(file)
                    # if 'filtered_css' is none, then assign ''
                    filtered_css = processed_file_info.get(
                        'filtered_css', '') or ''
                    filtered_css += '\n'
                    css_content += filtered_css
                    component_content[file_path] = {
                        'processed': True,
                        'content': processed_file_info['debug_component'],
                    }
            else:
                print('processing file:', file_path)
                if not os.path.exists(file_path):
                    continue
                with open(file_path, 'r') as file:
                    content = file.read()
                css_paths, content = self.find_css_imports(content)

                if file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                    component_content[file_path] = {
                        'processed': False,
                        'content': content,
                    }

                for css_path in css_paths:
                    full_css_path, is_local = self.resolve_import_path(
                        file_path, {'source': {'value': css_path}})
                    if full_css_path and os.path.exists(full_css_path) and full_css_path not in processed_css_files:
                        with open(full_css_path, 'r') as css_file:
                            raw_css = css_file.read()
                            if raw_css:
                                css_content += raw_css + "\n"
                        processed_css_files.add(full_css_path)

                        # statistics
                        self.add_statistic('total_css_files', 1)
        return css_content, component_content

    def extract_local_component_file_name(self, files):
        return [os.path.basename(file_path) for file_path in files]

    def is_local_import(self, import_path, component_names):
        extensions = ['.js', '.jsx', '.ts', '.tsx']
        import_name = os.path.basename(import_path)
        if '.' not in import_name:
            for ext in extensions:
                if f"{import_name}{ext}" in component_names:
                    return True
        else:
            if import_name in component_names:
                return True
        return False

    def gpt_filter_css(self, component_code, raw_style):
        if not component_code or not raw_style or raw_style == '':
            return raw_style, False
        example_component_code = 'function MyComponent() { return <div class="comp">comp test</div>; }'
        example_input_css = 'html {font-size: 16px;} \n img { width: 100px } \n .comp { color: red; } \n .footer { color: green }'
        example_output_css = 'html {font-size: 16px;} \n .comp { color: red; }'
        prompt = f'You will be given a self-contained React component code snippet and a CSS code snippet. You need to check the CSS code snippet and see if it could affect React component code snippet (according to the selector mechanism of CSS, for example style specification by tag name, id, class name, or even more complecated selection sepecification). You need to return a CSS code snippet that contains only the CSS properties that could affect the provided React component code snippet in rendering. For example, if the React component code snippet is defined as follows: \n{example_component_code}\n, and the CSS code snippet is defined as follows: \n{example_input_css}\n, then the output should be: \n{example_output_css}\n. REPLY WITH the filtered CSS code snippet only, no explanations, no comments, no qoutes wrapping the result code, no labels, and no any other text needed. Here is the React component code snippet: \n{component_code}\n\n and here is the CSS code snippet: \n{raw_style}\n\n, the filtered CSS code snippet should be:\n'
        gpt_result = llm_chat.chat(prompt)
        if gpt_result['content'] is None:
            return raw_style, False
        filtered_css = postprocess_code_reponse(gpt_result['content'])
        return filtered_css, False

    # return the filtered css content and has_gpt_err
    def add_mock_inputs(self, content):
        # 1st round to locate the input parameters
        prompt = 'You will be given a self-contained React component code snippet. You need to check all the components and see if they have any input parameters. you need to return a json object with the component name as the key and the value as a list of input parameters. If the component does not have any input parameters, the value should be an empty list. For example, if the component is defined as follows: function MyComponent(props) { return <div>{props.name}</div>; } The output should be: { "MyComponent": ["name"] }, REPLY WITH this json object only, no explanations, no comments, and no any other text needed. Here is the code snippet: '
        params_list_response = llm_chat.chat(prompt + content)

        # 2nd round to create mock input parameters
        if params_list_response['content'] is None:
            return content, False
        else:
            params_list = postprocess_code_reponse(
                params_list_response['content'])
            has_params = False
            for component, params in json.loads(params_list).items():
                if params and len(params) > 0:
                    has_params = True
                    break
            if has_params:
                prompt2 = 'Generate the necessary mock inputs for this React component based on the input parameters identified in the previous step. For each expected parameter, create appropriate mock data. If the parameter is a function, provide a function with the correct number of arguments and an empty body; for functions without parameters, use an empty function. For example, given the component definition function MyComponent(props) { return <div>{props.name}</div>; } and the parameters { "MyComponent": ["name"] }, the mock input should be { "name": "John" }. Update the component to use this mock input as its default, like so: function MyComponent(props = { "name": "John" }) { return <div>{props.name}</div>; }. Modify the original code minimally to incorporate these mock inputs, and do not change or ommit any part of the code if it is not related to incorporating the mock inputs. The response should include only the modified component code, without additional text, comments, or explanations.'
                chat_history = [{
                    'role': 'user',
                    'content': prompt + content
                }, {
                    'role': 'assistant',
                    'content': params_list
                }]
                updated_content = llm_chat.chat(
                    prompt2, chat_hist=chat_history)
                updated_content = postprocess_code_reponse(
                    updated_content['content'])
                if updated_content is None:
                    return content, False
                else:
                    return updated_content, False
            else:
                return content, False

    # return the fixed code content, whether the code is error free, code review result, and has_gpt_err
    def debug_code(self, content):
        system_prompt = 'We are conducting a static code review to ensure that a React component and all its sub-components are self-contained and error-free. This will involve checking if the default exported component can function independently by importing it without any additional local dependencies (third-party dependencies not included), ensuring all sub-components are also error-free. The review will proceed in two rounds: an initial evaluation followed by bug fixing if necessary.'
        round_1_prompt = 'Please assess the provided React component code, which includes the main component and its sub-components. Determine if the default exported component, including any third-party library imports, can be rendered as self-contained and without errors. Reply with "Yes" if there are no issues. If you find any problems, respond with "No" first and then describe the issues along with possible solutions. Here is the code snippet: \n'
        round_2_prompt = 'Please provide the entire corrected code for the default exported component and its sub-components, ensuring all parts are now self-contained and error-free. When addressing any missing elements, directly add the exact necessary content (e.g., defining missing variables or functions) within the code itself, instead of just including import statements. Change the code as less as possible to fix the errors, do not change or ommit any code that is not related to fixing the errors, Meanwhile the "default" export statement needs to be kept. Include both the revised and the error-free sections of the code to ensure the complete component is functional. REPLY ONLY WITH the complete code, no explanations, no labels, no qoutes wrapping the result code, no comments, and no any other text needed.'

        chat_history = [{
            'role': 'system',
            'content': system_prompt
        }]
        code_review_result = llm_chat.chat(
            round_1_prompt + content, chat_hist=chat_history)

        if code_review_result['content'] is None:
            return content, False, 'Error in code review should skip', False
       
        if code_review_result['content'][:3].lower() == 'yes':
            return content, True, code_review_result['content'], False
        else:
            chat_history.append({
                'role': 'user',
                'content': round_1_prompt + content
            })
            chat_history.append({
                'role': 'assistant',
                'content': code_review_result['content']
            })
            fixed_code = llm_chat.chat(round_2_prompt, chat_hist=chat_history)
            fixed_code = postprocess_code_reponse(fixed_code['content'])
            if fixed_code is None:
                return content, False, 'Error in code fixing should skip', False
            else:
                return fixed_code, False, code_review_result['content'], False

    def build_dependency_graph(self):
        graph = nx.DiGraph()
        for root, dirs, files in os.walk(self._repo_path):
            for file in files:
                if file.endswith(('.js', '.jsx', '.ts', '.tsx', '.css', '.scss', '.sass', '.less', '.styl')):
                    full_path = os.path.join(root, file)
                    graph.add_node(full_path)
                    try:
                        imports = []
                        if file.endswith(('.js', '.jsx', '.ts', '.tsx')):
                            imports = self.find_imports(full_path)
                        for imp in imports:
                            imp_path, is_local = self.resolve_import_path(
                                full_path, imp)
                            if imp_path:
                                graph.add_edge(full_path, imp_path)
                    except Exception as e:
                        print(f"Error processing file {full_path}: {e}")
                        tb = traceback.format_exc()
                        print(tb)
        print('------------------- dependency graph -------------------- ')
        for node in graph.nodes():
            print(f"File: {node}")
            for neighbor in graph.neighbors(node):
                print(f"  -> Depends on: {os.path.basename(neighbor)}")
        print('------------------- end dependency graph -------------------- ')
        return graph

    def collect_style_dependencies(self, start_node):
        styles = []
        # Collect paths from start node to all reachable nodes
        # Traverse all ancestors of the node
        for node in nx.ancestors(self._dependency_graph, start_node):
            if node.endswith(('.css', '.scss', '.sass', '.less', '.styl')):
                styles.append(node)
            elif node.endswith(('js', 'jsx', 'ts', 'tsx')):
                with open(node, 'r') as file:
                    content = file.read()
                    css_paths, file_content = self.find_css_imports(content)
                    styles += [os.path.join(os.path.dirname(node), css_path)
                               for css_path in css_paths]
        return styles

    def bundle_files(self, files, full_entry_component_path, entry_component_path):
        gpt_err = False
        css_content, component_content = self.distill_style_and_code(
            files)

        extra_css_paths = self.collect_style_dependencies(
            full_entry_component_path)

        extra_css_content = ''
        for extra_css_path in extra_css_paths:
            if not os.path.exists(extra_css_path):
                continue
            with open(extra_css_path, 'r') as css_file:
                raw_css = css_file.read()
                extra_css_content += raw_css + '\n'

        component_content_str = ''
        component_file_paths = list(component_content.keys())
        sorted_component_file_paths = self.topological_sort_files(
            component_file_paths)
        # sub_components_token_num = {}
        sub_components = []
        for file_path in sorted_component_file_paths:
            processed = component_content[file_path]['processed']
            content = component_content[file_path]['content']

            is_entry_component = (os.path.basename(
                file_path).startswith(entry_component_path))
            if not is_entry_component:
                content = re.sub(r'export\s+default.*', '', content)

            # add mock inputs with gpt
            has_gpt_err = False
            if processed:
                # no need to ask gpt to add mock inputs
                has_gpt_err = False
            else:
                sub_components.append(file_path)
                content, has_gpt_err = self.add_mock_inputs(content)
            if has_gpt_err:
                return None, True

            component_content_str += content + '\n\n'

        regex_component_imports = r"import\s+(?:(\w+)(?:,\s*)?)?(?:\{([\w\s,]+)\})?\s*from\s+['\"]([^'\"]+?)['\"]"
        import_statements = re.findall(
            regex_component_imports, component_content_str)
        default_imports = set()
        named_imports = set()
        component_file_names = self.extract_local_component_file_name(files)
        for default_import, named_imports_str, import_path in import_statements:
            if default_import:
                if not self.is_local_import(import_path, component_file_names):
                    default_imports.add((default_import, import_path))
            if named_imports_str:
                if not self.is_local_import(import_path, component_file_names):
                    named_imports.update(
                        [(named_import.strip(), import_path) for named_import in named_imports_str.split(',')])

        import_statements_str = ''
        for default_import, import_path in default_imports:

            import_statements_str += f"import {default_import} from '{import_path}';\n"
        for named_import, import_path in named_imports:
            import_statements_str += f"import {{{named_import}}} from '{import_path}';\n"

        # remove all import statements, remove redundant import statements and put the import statements at the top
        regex_remove_import_lines = r"^.*import\s+(?:\* as \w+|{?\s*[\w\s,]*}?\s*(?:as\s+\w+)?(?:,\s*{[\w\s,]*}\s*)?)from\s+['\"].*?['\"].*$"
        component_content_str = re.sub(
            regex_remove_import_lines, '', component_content_str, flags=re.MULTILINE)
        component_content_str = import_statements_str + '\n\n' + component_content_str

        raw_style = extra_css_content + '\n' + css_content
        # filter out from raw_style and keep the style specification that could affect the component
        filtered_css, has_gpt_err = self.gpt_filter_css(
            component_content_str, raw_style)
        if has_gpt_err:
            return None, True

        # debug the code
        debug_component_content_str, bug_free, explaination, has_gpt_err = self.debug_code(
            component_content_str)
        if has_gpt_err:
            return None, True
        # bundled_content = f"// raw CSS Styling\n`{raw_style}`\n// end raw CSS Styling\n\n// filtered CSS Styling\n`{filtered_css}`\n// end filtered CSS Styling\n\n{debug_component_content_str}"
        bundled_json = {
            'raw_css': raw_style,
            'filtered_css': filtered_css,
            "sub_components": sub_components,
            # 'sub_components_token_num': sub_components_token_num,
            'raw_component': component_content_str,
            # 'raw_component_tokens': component_token_num,
            'bug_free': bug_free,
            'explaination': explaination,
            'debug_component': debug_component_content_str,
        }

        return bundled_json, False

    def copy_package_json(self):
        package_json = self.read_file(self._repo_path, 'package.json')
        if package_json:
            with open(os.path.join(self._output_dir, 'package.json'), 'w') as f:
                f.write(package_json)

    def identify_component_file_type(self, file_path):
        file_type = 'js'
        if file_path.endswith('.jsx'):
            file_type = 'jsx'
        elif file_path.endswith('.ts'):
            file_type = 'ts'
        elif file_path.endswith('.tsx'):
            file_type = 'tsx'
        return file_type

    def topological_sort_files(self, filenames):
        subgraph = self._dependency_graph.subgraph([
            f for f in filenames if f in self._dependency_graph
        ])
        try:
            sorted_paths = list(nx.topological_sort(subgraph))
            sorted_paths.reverse()
            return sorted_paths
        except nx.NetworkXUnfeasible:
            print("A cycle was detected in the graph. Topological sort is not possible.")
            return filenames

    # return whether successfully processed the component, and has_gpt_err
    def process_component(self, component_path):
        print('=================================================================')
        print(f"Processing {component_path}...")

        # Collect all the dependencies recursively
        try:
            file_type = self.identify_component_file_type(component_path)
            output_filename = os.path.basename(
                component_path).replace(f'.{file_type}', '_bundled.json')
            output_path = os.path.join(self._output_dir, output_filename)
            # check if the file already exists
            if os.path.exists(output_path):
                print(f"File {output_path} already exists. Skipping...")
                return True, False

            all_files = self.recursive_imports(component_path)
            print(f'all files for {component_path}: {all_files}')
            # Bundle the files into a single chunk of content
            bundled_json, has_gpt_err = self.bundle_files(
                all_files, component_path, os.path.basename(component_path))

            if has_gpt_err:
                return False, True

            if not bundled_json:
                self.add_statistic('total_components_failed', 1)
                return False, False
            # identify the file type
            bundled_json['file_type'] = file_type

            self._processed_files[component_path] = output_path
            print(f"-- Writing bundled content to {output_path}")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w') as output_file:
                json.dump(bundled_json, output_file, indent=4)
            return True, False
        except Exception as e:
            print(f"Error processing component {component_path}: {e}")
            tb = traceback.format_exc()
            print(tb)
            self.add_statistic('total_components_failed', 1)
            return False, False

    def process_repo(self):
        print(
            f'----------- start processing {self._repo_path} -----------------')
        # copy the package.json file to the output directory
        self.copy_package_json()

        # Build the dependency graph for the project
        self._dependency_graph = self.build_dependency_graph()

        # Find all React components in the project
        all_files = self.find_all_files()

        component_files = self.find_react_components()
        print(
            f"Found {len(component_files)}/{len(all_files)} components in {self._repo_path}.")
        print('all_files:', all_files)
        print('component_files:', component_files)

        sorted_component_files = self.topological_sort_files(component_files)
        failed_components = set()
        for component_path in tqdm(sorted_component_files, desc='Processing components'):
            try:
                success, has_gpt_err = self.process_component(component_path)
                if has_gpt_err:
                    failed_components.add(component_path)
                    print(f"llm is down!!!!!")
                    return False
                if not success:
                    failed_components.add(component_path)
                    print(f"Failed to process component {component_path}")
                # break
            except Exception as e:
                print(f"Error processing component {component_path}: {e}")
                failed_components.add(component_path)
                tb = traceback.format_exc()
                print(tb)
                continue

        repo_component_count = {
            'total_components': len(sorted_component_files),
            'failed_components': list(failed_components),
        }

        self.update_statistic('failed_components', {
            'repo': self._repo_path,
            'count': repo_component_count
        })

        # create a temp file to store the failed components
        failed_components_file = os.path.join(
            self._repo_path, 'failed_components.json')
        with open(failed_components_file, 'w') as f:
            json.dump(list(failed_components), f, indent=4)

        print(
            f'----------- end processing {self._repo_path} -----------------')

        return True

    def read_file(self, base_path, file):
        path = os.path.join(base_path, file)
        if os.path.exists(path):
            if os.path.isfile(path):
                with open(path, 'r') as f:
                    return f.read()
        return None


class Util():
    def __init__(self):
        pass

    def get_repos(self, path):
        if not os.path.exists(path):
            print(f"Path {path} does not exist.")
            return []
        repo_paths = []
        for repo in os.listdir(path):
            repo_path = os.path.join(path, repo)
            repo_paths.append(repo_path)
        print(f"Found {len(repo_paths)} unprocessed repositories in {path}.")
        return repo_paths


def count_components(base_path, repo_path, output_path, lock):
    tmp_distiller = Distiller(
        base_path=base_path,
        repo_path=repo_path,
        output_dir=output_path,
        statistic={},
        lock=lock)
    component_files = tmp_distiller.find_react_components(False)
    return len(component_files)


def sort_repos_by_components(base_path, repo_paths, output_path, lock):
    return sorted(repo_paths, key=lambda x: count_components(base_path, x, output_path, lock))


def process_repositories_in_batches(base_path, repo_paths, output_path, max_workers, lock, statistic):
    # sort the repos based on the number of components
    print('sorting repos based on the number of components...')
    sorted_repo_paths = sort_repos_by_components(
        base_path, repo_paths, output_path, lock)

    # Split sorted_repo_paths into chunks of size max_workers
    batches = [sorted_repo_paths[i:i + max_workers]
               for i in range(0, len(sorted_repo_paths), max_workers)]

    print(
        f"Processing {len(sorted_repo_paths)} repositories in {len(batches)} batches.")
    for batch_index, batch in tqdm(enumerate(batches), total=len(batches), desc='Processing Batches'):
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(Distiller(
                base_path=base_path,
                repo_path=repo_path,
                output_dir=output_path,
                statistic=statistic,
                lock=lock).process_repo): repo_path for repo_path in batch}
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc=f'Processing Batch {batch_index + 1}/{len(batches)}'):
                repo_path = futures[future]
                try:
                    success = future.result()
                    if not success:
                        print(
                            f"Failed to process repository {repo_path} cause of gpt error")
                        return
                    print(f"Repository processed successfully: {repo_path}")
                    # break
                except Exception as e:
                    print(f"Error processing repository {repo_path}: {e}")
                    tb = traceback.format_exc()
                    print(tb)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--threads', type=int, default=30)
    parser.add_argument('--repo_path', type=str)
    parser.add_argument('--output_path', type=str)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    threads = args.threads
    base_dir = os.path.dirname(os.path.abspath(__file__))
    repo_path = args.repo_path
    output_path = args.output_path

    print(f"BASE_DIR: {base_dir}")
    print(f"REPO_WORKSPACE: {repo_path}")
    print(f"OUTPUT_DIR: {output_path}")

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    statistic = {
        'total_repos': 0,
        'total_components': 0,
        'total_files': 0,
        'total_css_files': 0,
        'total_js_files': 0,
        'total_ts_files': 0,
        'total_jsx_files': 0,
        'total_tsx_files': 0,
        'total_components_with_params': 0,
        'total_components_failed': 0,
        'model_requests': 0,
        'model_tokens': 0,
        'failed_components': []
    }
    lock = Lock()
    # init statistics with existing data in file
    if os.path.exists(os.path.join(output_path, 'statistic.json')):
        with open(os.path.join(output_path, 'statistic.json'), 'r') as f:
            statistic = json.load(f)

    util = Util()
    repo_paths = util.get_repos(repo_path)
    print(f'found {len(repo_paths)} repos to process.')
    statistic['total_repos'] += len(repo_paths)

    process_repositories_in_batches(
        base_path=base_dir,
        repo_paths=repo_paths,
        output_path=output_path,
        max_workers=threads,
        lock=lock,
        statistic=statistic)

    print('done')
