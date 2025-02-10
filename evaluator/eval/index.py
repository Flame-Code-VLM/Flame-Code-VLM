import argparse
import io
import re
import subprocess
import time
import requests
import json
import cv2
import pytesseract
import os
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import sys
import uuid
from PIL import Image
from skimage.metrics import structural_similarity as ssim
from skimage.filters import sobel
from skimage.feature import canny

sys.setrecursionlimit(2000)  #

IP = '<SERVER_IP>'
ports = [9999]
GEN_NUM = 50


class Evaluator:
    def cosine_similarity(self, vec1, vec2):
        dot_product = np.dot(vec1, vec2)
        norm_a = np.linalg.norm(vec1)
        norm_b = np.linalg.norm(vec2)
        cosine_similarity = dot_product / (norm_a * norm_b)
        return cosine_similarity

    def compute_img_embedding_similarity(self, generated_img_path, reference_img_path, port):
        if not os.path.exists(generated_img_path) or not os.path.exists(reference_img_path):
            return 0.0

        # padding images to the same size
        gen_img = Image.open(generated_img_path)
        ref_img = Image.open(reference_img_path)

        gen_img_size = gen_img.size
        ref_img_size = ref_img.size

        target_width = max(gen_img_size[0], ref_img_size[0])
        target_height = max(gen_img_size[1], ref_img_size[1])

        new_gen_img = Image.new('RGB', (target_width, target_height))
        new_gen_img.paste(gen_img, (0, 0))
        new_ref_img = Image.new('RGB', (target_width, target_height))
        new_ref_img.paste(ref_img, (0, 0))

        def embed_img(image):
            url = f"http://{IP}:{port}/infer"
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            binary_data = buffer.getvalue()
            files = {'file': (f'image_{uuid.uuid4().hex}.png',
                              binary_data, 'image/png')}

            response = requests.post(url, files=files)
            if response.status_code == 200:
                result = response.json()

                last_hidden_state_list = np.array(
                    result.get('last_hidden_state_list', []))[0]
                # print('last_hidden_state_list: ', last_hidden_state_list.shape)
                if last_hidden_state_list.size > 0:
                    avg_hidden_state = np.mean(
                        last_hidden_state_list, axis=0)
                    # print('avg_hidden_state: ', avg_hidden_state.shape)
                    return avg_hidden_state
                else:
                    return None
            else:
                print("Error:", response.status_code, response.text)
                return None
        gen_embedding = embed_img(new_gen_img)
        ref_embedding = embed_img(new_ref_img)

        if gen_embedding is None or ref_embedding is None:
            print("Failed to encode one or both images.")
            return 0.0

        gen_img_encode = np.array(gen_embedding)
        ref_img_encode = np.array(ref_embedding)
        similarity = self.cosine_similarity(gen_img_encode, ref_img_encode)
        return similarity

    def is_error_image(self, image):
        text = pytesseract.image_to_string(image)
        error_keywords = ['error', 'failure',
                          'not found', 'invalid', 'timeout']
        for keyword in error_keywords:
            if keyword in text.lower():
                return True

        return False

    def is_blank_image(self, image):
        first_pixel = image[0, 0]
        return np.all(image == first_pixel)

    def img_has_error(self, image_path):
        image = cv2.imread(image_path)
        if image is None:
            print(f"Failed to load image: {image_path}")
            return True
        if self.is_blank_image(image):
            return True

        if self.is_error_image(image):
            return True
        return False

    def call_nodejs_function(self, gen_code, ref_code):
        result = subprocess.run(
            ['node', 'evaluator/eval/code_evaluator/score.js',
                str(gen_code), str(ref_code)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return json.loads(result.stdout.strip())
        else:
            raise Exception(f"Node.js script failed: {result.stderr}")

    def score(self, generated_img_path, reference_img_path, gen_code, ref_code, repeat, port):
        code_score_result = self.call_nodejs_function(gen_code, ref_code)
        code_score = float(code_score_result['genScore'])
        print('-'*20)
        print('code_score: ', code_score_result, code_score, type(code_score))
        img_name = os.path.basename(generated_img_path).split('.')[0]
        result = {
            'img_name': f'img_{img_name}',
            'img_similarity': 0.0,
            'code_similarity': code_score,
            'img_code_similarity': 0.0
        }

        if not os.path.exists(generated_img_path):
            return [result] * repeat

        # check whether the image is too large
        try:
            with Image.open(generated_img_path) as img:
                width, height = img.size
                if width > 4096 or height > 4096:
                    print(
                        f"Image is too large: {img_name} ({width}x{height}), cropping to 4096x4096")
                    left = max(0, (width - 4096) // 2)
                    top = max(0, (height - 4096) // 2)
                    right = min(width, left + 4096)
                    bottom = min(height, top + 4096)
                    img = img.crop((left, top, right, bottom))
                    cropped_img_path = os.path.join(os.path.dirname(
                        generated_img_path), f"cropped_{img_name}.png")
                    img.save(cropped_img_path)
                    generated_img_path = cropped_img_path
        except Exception as e:
            print(f"Error processing image: {img_name}, {e}")
            return [result] * repeat

        if self.img_has_error(generated_img_path):
            # print("Error image detected")
            return [result] * repeat

        futures = []
        with ThreadPoolExecutor(max_workers=30) as executor:
            futures.append(executor.submit(self.compute_img_embedding_similarity,
                                           generated_img_path, reference_img_path, port))
        for future in as_completed(futures):
            img_similarity = future.result()
            result['img_similarity'] = img_similarity
            result['img_code_similarity'] = img_similarity * code_score

        return [result] * repeat

    def load_test_data(self, test_data_path):
        with open(test_data_path, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        return test_data

    def translate_content_type(self, matched_pattern):
        if matched_pattern == "// JavaScript (JS)":
            return "js"
        elif matched_pattern == "// TypeScript (TS)":
            return "ts"
        elif matched_pattern == "// JavaScript XML (JSX)":
            return "jsx"
        elif matched_pattern == "// TypeScript XML (TSX)":
            return "tsx"
        else:
            return "jsx" 

    def process_strings(self, input_str):
        split_patterns = [
            r"(\/\/ JavaScript \(JS\))",
            r"(\/\/ TypeScript \(TS\))",
            r"(\/\/ JavaScript XML \(JSX\))",
            r"(\/\/ TypeScript XML \(TSX\))"
        ]

        pattern = re.compile("|".join(split_patterns))

        match = pattern.search(input_str)

        if match:
            matched_pattern = match.group(0)
            split_index = match.start()

            first_part = input_str[:split_index].strip()
            second_part = input_str[split_index +
                                    len(matched_pattern):].strip()

            first_part = re.sub(r'^\/\/ CSS', '', first_part).strip()

            return [first_part, self.translate_content_type(matched_pattern), second_part]
        else:
            cleaned_str = re.sub(r'^\/\/ CSS', '', input_str).strip()
            return [cleaned_str, 'jsx', '']

    def extract_component_code(self, output):
        tmp_style, tmp_type, tmp_code = self.process_strings(output)

        if tmp_code:
            return [tmp_style, tmp_type, tmp_code]
        index = output.find("import ")

        style = ''
        component = ''

        if index == -1:
            return [re.sub(r'^\/\/ CSS', '', output).strip(), 'jsx', '']

        style = re.sub(r'^\/\/ CSS', '', output[:index]).strip()
        component = output[index:].strip()

        return [style, 'jsx', component]

    def load_gen_codes(self, model_name, gen_code_dir):
        codes = json.load(
            open(os.path.join(gen_code_dir, f'{model_name}_results.json'), 'r'))
        problem_index_codes = {}
        for code in codes:
            tmp_id = code['id']
            # convert the id to string with 9 digits, e.g., 1 -> 000000001
            tmp_id = str(tmp_id).zfill(9)
            if tmp_id not in problem_index_codes:
                problem_index_codes[tmp_id] = {}
            tmp_style, tmp_type, tmp_code = self.extract_component_code(
                code['output'])
            problem_index_codes[tmp_id][f'index_{code["index"]}'] = {
                'code': tmp_code,
                'repeat': code['repeat'],
            }
        return problem_index_codes

    def locate_test_data(self, problem_id, test_data):
        for data in test_data:
            if data['problem_id'] == problem_id:
                return data
        return None

    def estimator(self, n: int, c: int, k: int) -> float:
        """
        Calculates 1 - comb(n - c, k) / comb(n, k).
        """
        if n - c < k:
            return 1.0
        return 1.0 - np.prod(1.0 - k / np.arange(n - c + 1, n + 1))

    def for_file(self, score_list, threshold):
        n = len(score_list)
        c = len(
            [True for score in score_list if score >= threshold]
        )
        # pass@1, pass@3, pass@5
        return np.array([self.estimator(n, c, 1), self.estimator(n, c, 3), self.estimator(n, c, 5)])
        # return np.array([estimator(n, c, 1), estimator(n, c, 10), estimator(n, c, 100)])

    def score_problem(self, model_name, problem_id, problem_complexity, gen_codes, reference_img_path, reference_code, port, gen_img_dir):
        # if problem_id != '000000001':
        #     return None
        score_for_problem = []
        for index_str in gen_codes[problem_id]:
            index = index_str.split('_')[1]
            img_name = f'{problem_id}_{index}_0.png'
            img_path = os.path.join(
                gen_img_dir, model_name, img_name)
            gen_code_repeat = gen_codes[problem_id][index_str]
            score_for_problem += self.score(
                img_path, reference_img_path, gen_code_repeat['code'], reference_code, gen_code_repeat['repeat'], port)
            # break

        if len(score_for_problem) < GEN_NUM:
            print(
                f"Warning: only {len(score_for_problem)} images were scored for problem {problem_id}.")
            score_for_problem += [{'img_name': 'img_0',
                                   'img_similarity': 0.0,
                                   'code_similarity': 0.0,
                                   'img_code_similarity': 0.0} for i in range(GEN_NUM - len(score_for_problem))]

        return {
            'problem_id': problem_id,
            'problem_complexity': problem_complexity,
            'scores': score_for_problem
        }

    def process_gen_result(self, model_name, gen_codes, test_data, port, gen_img_dir):
        def process_problem(problem_id):
            corresponding_test_data = self.locate_test_data(
                problem_id, test_data)
            if corresponding_test_data:
                problem_complexity = corresponding_test_data['complexity_level']
                reference_code = corresponding_test_data['component']
                reference_img_path = os.path.join(os.path.dirname(os.path.abspath(
                    __file__)), '../prepareTest', corresponding_test_data['image'])

                return self.score_problem(model_name, problem_id, problem_complexity, gen_codes, reference_img_path, reference_code, port, gen_img_dir)
            return None

        all_scores = []

        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(process_problem, problem_id)
                       for problem_id in gen_codes]

            for future in tqdm(as_completed(futures), total=len(futures), desc="Processing problems"):
                result = future.result()
                if result is not None:
                    all_scores.append(result)
                # break

        return all_scores

    def run_eval(self, test_data_path, model_name, gen_code_dir, gen_img_dir):
        eval_start_time = time.time()
        gen_codes = self.load_gen_codes(model_name, gen_code_dir)
        print(f'loaded {model_name} gen codes')
        test_data = self.load_test_data(test_data_path)
        print('done load test data')
        all_scores = self.process_gen_result(
            model_name, gen_codes, test_data, ports[0], gen_img_dir)
        eval_end_time = time.time()
        print(f"Evaluation time: {eval_end_time - eval_start_time} seconds")

        # print("All scores:", all_scores)

        # transform all_scores to 2d array
        all_img_scores_list = []
        all_code_scores_list = []
        all_img_code_scores_list = []
        img_scores_list_by_complexity = {}
        code_scores_list_by_complexity = {}
        img_code_scores_list_by_complexity = {}
        for item in all_scores:
            tmp_img_scores = []
            tmp_code_scores = []
            tmp_img_code_scores = []
            problem_complexity = f"level_{item['problem_complexity']}"

            for score_item in item['scores']:
                tmp_img_scores.append(score_item['img_similarity'])
                tmp_code_scores.append(score_item['code_similarity'])
                tmp_img_code_scores.append(score_item['img_code_similarity'])

            if not problem_complexity in img_scores_list_by_complexity:
                img_scores_list_by_complexity[problem_complexity] = []
            if not problem_complexity in code_scores_list_by_complexity:
                code_scores_list_by_complexity[problem_complexity] = []
            if not problem_complexity in img_code_scores_list_by_complexity:
                img_code_scores_list_by_complexity[problem_complexity] = []

            img_scores_list_by_complexity[problem_complexity].append(
                tmp_img_scores)
            code_scores_list_by_complexity[problem_complexity].append(
                tmp_code_scores)
            img_code_scores_list_by_complexity[problem_complexity].append(
                tmp_img_code_scores)

            all_img_scores_list.append(tmp_img_scores)
            all_code_scores_list.append(tmp_code_scores)
            all_img_code_scores_list.append(tmp_img_code_scores)

        # print('-'*100)
        # print(all_img_scores_list)
        print("All scores:", len(all_img_scores_list), len(
            all_img_scores_list[0]), all_img_scores_list[0][0])
        print("All code scores:", len(all_code_scores_list), len(
            all_code_scores_list[0]), all_code_scores_list[0][0])
        print("All scores by complexity:", len(img_scores_list_by_complexity),
              len(img_scores_list_by_complexity['level_0']), len(img_scores_list_by_complexity['level_1']), len(img_scores_list_by_complexity['level_2']), len(img_scores_list_by_complexity['level_0'][0]), img_scores_list_by_complexity['level_0'][0][0])

        # thresholds = [0.6, 0.7, 0.8, 0.9]
        thresholds = [0.7, 0.8, 0.85, 0.9, 0.95, 0.99]
        pass_at_1_img_results = {}
        pass_at_1_code_results = {}
        pass_at_1_img_code_results = {}
        pass_at_3_img_code_results = {}
        pass_at_5_img_code_results = {}

        pass_at_1_img_results_by_complexity = {}
        pass_at_1_code_results_by_complexity = {}
        pass_at_1_img_code_results_by_complexity = {}
        for threshold in thresholds:
            tmp_img_results_array = np.array(
                [self.for_file(scores, threshold) for scores in all_img_scores_list])
            tmp_img_results = tmp_img_results_array.mean(axis=0)
            # print(f"Threshold: {threshold}, Pass@1: {tmp_results[0]}")
            pass_at_1_img_results[threshold] = round(
                tmp_img_results[0], 4)  # pass@1

            tmp_code_results_array = np.array(
                [self.for_file(scores, threshold) for scores in all_code_scores_list])
            tmp_code_results = tmp_code_results_array.mean(axis=0)
            # print(f"Threshold: {threshold}, Pass@1: {tmp_results[0]}")
            pass_at_1_code_results[threshold] = round(
                tmp_code_results[0], 4)  # pass@1

            tmp_img_code_results_array = np.array(
                [self.for_file(scores, threshold) for scores in all_img_code_scores_list])
            tmp_img_code_results = tmp_img_code_results_array.mean(axis=0)
            # print(f"Threshold: {threshold}, Pass@1: {tmp_results[0]}")
            pass_at_1_img_code_results[threshold] = round(
                tmp_img_code_results[0], 4)  # pass@1

            pass_at_3_img_code_results[threshold] = round(tmp_img_code_results[1], 4)
            pass_at_5_img_code_results[threshold] = round(tmp_img_code_results[2], 4)

            for problem_complexity in img_scores_list_by_complexity:
                tmp_img_results_array = np.array(
                    [self.for_file(scores, threshold) for scores in img_scores_list_by_complexity[problem_complexity]])
                tmp_img_results = tmp_img_results_array.mean(axis=0)
                if not problem_complexity in pass_at_1_img_results_by_complexity:
                    pass_at_1_img_results_by_complexity[problem_complexity] = {
                    }
                pass_at_1_img_results_by_complexity[problem_complexity][threshold] = round(
                    tmp_img_results[0], 4)

            for problem_complexity in code_scores_list_by_complexity:
                tmp_code_results_array = np.array(
                    [self.for_file(scores, threshold) for scores in code_scores_list_by_complexity[problem_complexity]])
                tmp_code_results = tmp_code_results_array.mean(axis=0)
                if not problem_complexity in pass_at_1_code_results_by_complexity:
                    pass_at_1_code_results_by_complexity[problem_complexity] = {
                    }
                pass_at_1_code_results_by_complexity[problem_complexity][threshold] = round(
                    tmp_code_results[0], 4)

            for problem_complexity in img_code_scores_list_by_complexity:
                tmp_img_code_results_array = np.array(
                    [self.for_file(scores, threshold) for scores in img_code_scores_list_by_complexity[problem_complexity]])
                tmp_img_code_results = tmp_img_code_results_array.mean(axis=0)
                if not problem_complexity in pass_at_1_img_code_results_by_complexity:
                    pass_at_1_img_code_results_by_complexity[problem_complexity] = {
                    }
                pass_at_1_img_code_results_by_complexity[problem_complexity][threshold] = round(
                    tmp_img_code_results[0], 4)

        print_str = "Pass@1 for img_code of all problems:" + '\t'.join([str(pass_at_1_img_code_results[threshold])
                                                                        for threshold in thresholds]) + '\n'
        print_str += "Pass@3 for img_code of all problems:" + '\t'.join([str(pass_at_3_img_code_results[threshold])
                                                                        for threshold in thresholds]) + '\n'
        print_str += "Pass@5 for img_code of all problems:" + '\t'.join([str(pass_at_5_img_code_results[threshold])
                                                                        for threshold in thresholds]) + '\n'

        record = {
            'all_img_scores': all_img_scores_list,
            'all_code_scores': all_code_scores_list,
            'all_img_code_scores': all_img_code_scores_list,
            'pass_at_1_img_results': pass_at_1_img_results,
            'pass_at_1_code_results': pass_at_1_code_results,
            'pass_at_1_img_code_results': pass_at_1_img_code_results,
            'pass_at_1_img_results_by_complexity': pass_at_1_img_results_by_complexity,
            'pass_at_1_code_results_by_complexity': pass_at_1_code_results_by_complexity,
            'pass_at_1_img_code_results_by_complexity': pass_at_1_img_code_results_by_complexity,
            'print_str': print_str,
            'gen_num': GEN_NUM
        }
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f'results/pass_at_k_results_{model_name}.json'), 'w', encoding='utf-8') as f:
            json.dump(record, f, ensure_ascii=False, indent=4)

        print(print_str)
        print('='*100)


def parse_arguments():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--test_data_path', type=str)
    parser.add_argument('--model_name', type=str)
    parser.add_argument('--gen_code_dir', type=str)
    parser.add_argument('--gen_img_dir', type=str)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    evaluator = Evaluator()
    evaluator.run_eval(args.test_data_path, args.model_name,
                       args.gen_code_dir, args.gen_img_dir)
    print('done')
