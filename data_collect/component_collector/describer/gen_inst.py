import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import shutil

import cv2
from tqdm import tqdm
from utils.util import postprocess_code_reponse
from utils.llm import chat
import os
import re
from PIL import Image


CROP_WIDTH = 800
CROP_HEIGHT = 600
BATCH_SIZE = 100


def load_processed_images(path):
    """Load the list of processed images."""
    if not os.path.exists(path):
        return set()
    with open(path, 'r') as f:
        return {json.loads(line)['image'] for line in f}


def load_pregenerated_inst(path):
    """Load the list of pregenerated instructions."""
    if not os.path.exists(path):
        return []
    with open(path, 'r') as f:
        result = {}
        for line in f:
            data = json.loads(line)
            result[data['image']] = {
                'layout': data['instruction_layout'],
                'requirement': data['instruction_requirement'],
            }
        return result


def generate_inst_with_llm(comp_code, style_code):
    prompt = 'Based on the following React code and its associated CSS, please analyze and generate the following two parts of the description:\n\n1. Describe the possible appearance of the page rendered by this code. Provide a detailed account of the layout configuration, including the arrangement, size, color, and type of components. Specify the exact position of each component (e.g., at the top, centered, or at the bottom of the page), as well as the relationships and interactions between these components.\n\n2.Parse the functional requirements of this code. Assume this corresponds to a specific user requirement; please describe this requirement in the user\'s voice. For example, if the code implements a registration form, the requirement could be described as: "I need a simple user registration form where users can enter their name, email, and password, along with a submit button."\n\nPlease output the analysis results in JSON format, including two fields: \'layout\' and \'requirement.\' The \'layout\' field should provide a detailed description of the page layout and the appearance of the components, while the \'requirement\' field should explain the user need that the code fulfills.\n\nNote:\n\n- The content of the fields in the JSON should be described in English.\n- Ensure the JSON format is correct; otherwise, your response cannot be parsed.\n- Include only one JSON object in your response; do not add any comments, explanations, or additional content.\n- Do not generate duplicate content.\n- The contents of the layout and requirement fields in the JSON object should be confirmed as a single string each, with no additional formatting (no JSON, markdown, etc.).'
    prompt += f'\n\nReact code: \n{comp_code}\n\nCSS code: \n{style_code}'

    reponse = chat(prompt)
    if not reponse:
        return None

    jsonStr = postprocess_code_reponse(reponse)
    if jsonStr:
        try:
            result = json.loads(jsonStr)
            return result
        except:
            print(f'error parsing json: {jsonStr}')
            return None


def translate_file_type(file_type):
    file_type = file_type.lower().strip()
    if file_type == 'js':
        return 'JavaScript (JS)'
    if file_type == 'ts':
        return 'TypeScript (TS)'
    if file_type == 'jsx':
        return 'JavaScript XML (JSX)'
    if file_type == 'tsx':
        return 'TypeScript XML (TSX)'
    return file_type


def crop_image_cv2(source_img_path, cropped_img_path):
    """Crop or pad the image using OpenCV and save it."""
    try:
        # Load the image with alpha channel if available
        img = cv2.imread(source_img_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            print(f"Error loading image {source_img_path}")
            return 0, 0

        height, width = img.shape[:2]

        if width < CROP_WIDTH or height < CROP_HEIGHT:
            pad_width = max(0, CROP_WIDTH - width)
            pad_height = max(0, CROP_HEIGHT - height)
            top, bottom = pad_height // 2, pad_height - pad_height // 2
            left, right = pad_width // 2, pad_width - pad_width // 2
            img = cv2.copyMakeBorder(
                img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(255, 255, 255, 0))

        start_x = (img.shape[1] - CROP_WIDTH) // 2
        start_y = (img.shape[0] - CROP_HEIGHT) // 2

        cropped_img = img[start_y:start_y +
                          CROP_HEIGHT, start_x:start_x + CROP_WIDTH]
        cv2.imwrite(cropped_img_path, cropped_img)

        return width, height
    except Exception as e:
        print(f"Error cropping image {source_img_path}: {e}")
        return 0, 0


def process_file(file, root, processed_images, pregenerated_inst, code_dir, ori_img_dir, cropped_img_dir):
    if file in processed_images or not file.lower().endswith('.png'):
        return None

    repo_name, comp_name = file.replace('.png', '').split('-_-_-')
    code_file_path = os.path.join(code_dir, repo_name, comp_name)

    if not os.path.exists(code_file_path):
        return None

    try:
        with open(code_file_path, 'r') as f:
            code = json.load(f)

        source_img_path = os.path.join(root, file)
        shutil.copy2(source_img_path, ori_img_dir)

        cropped_img_name = f"cropped_{file}"
        cropped_img_path = os.path.join(cropped_img_dir, cropped_img_name)
        ori_img_width, ori_img_height = crop_image_cv2(
            source_img_path, cropped_img_path)

        target_code = code['code_with_ori_img']
        if file in pregenerated_inst:
            inst = pregenerated_inst[file]
        else:
            inst = generate_inst_with_llm(target_code, code['filtered_css'])

        file_type = code['file_type']
        prefix = translate_file_type(file_type)

        if inst:
            return {
                'meta_data': {
                    'repo_name': repo_name,
                    'component_name': comp_name,
                    'preview': cropped_img_name if ori_img_width != 0 else file,
                    'width': ori_img_width,
                    'height': ori_img_height,
                },
                'image': file,
                'instruction_layout': inst['layout'],
                'instruction_requirement': inst['requirement'],
                'style': '// CSS\n' + code["filtered_css"],
                'component': f'// {prefix}\n{target_code}',
                'code': f'// CSS\n{code["filtered_css"]}\n\n// {prefix}\n{target_code}',
            }
    except Exception as e:
        print(f"Error processing file {file}: {e}")
    return None


def batch_write(data, path, starting_id):
    """Write data in batches to avoid excessive I/O."""
    if not data:
        return
    with open(path, 'a', encoding='utf-8') as f:
        for i, item in enumerate(data):
            item['id'] = starting_id + i  # Assign a unique ID to each record
            json.dump(item, f, ensure_ascii=False)
            f.write('\n')


def get_next_id(inst_data_path):
    """Compute the next ID based on the contents of inst_data.jsonl."""
    if not os.path.exists(inst_data_path):
        return 0
    max_id = 0
    with open(inst_data_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                max_id = max(max_id, data.get('id', 0))
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
    return max_id + 1


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--screenshot_path', type=str)
    parser.add_argument('--code_path', type=str)
    parser.add_argument('--inst_path', type=str)
    parser.add_argument('--ori_img_path', type=str)
    parser.add_argument('--cropped_img_path', type=str)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    screenshot_path = args.screenshot_path
    code_path = args.code_path
    inst_path = args.inst_path
    ori_img_path = args.ori_img_path
    cropped_img_path = args.cropped_img_path

    os.makedirs(inst_path, exist_ok=True)
    os.makedirs(ori_img_path, exist_ok=True)
    os.makedirs(cropped_img_path, exist_ok=True)
    inst_data_path = os.path.join(inst_path, 'inst_data_v2.jsonl')

    processed_images = load_processed_images(inst_data_path)

    pregenerated_inst = load_pregenerated_inst(
        os.path.join(inst_path, 'inst_data.jsonl'))
    print(f'Loaded {len(pregenerated_inst)} pregenerated instructions.')

    inst_data_list = []
    starting_id = get_next_id(inst_data_path)

    with ThreadPoolExecutor(max_workers=500) as executor:
        futures = []
        for root, _, files in tqdm(os.walk(screenshot_path), desc='Walking files'):
            for file in files:
                futures.append(executor.submit(
                    process_file, file, root, processed_images, pregenerated_inst, code_path, ori_img_path, cropped_img_path))

        for future in tqdm(as_completed(futures), total=len(futures), desc='Processing images'):
            result = future.result()
            if result:
                inst_data_list.append(result)

            if len(inst_data_list) >= BATCH_SIZE:
                batch_write(inst_data_list, inst_data_path, starting_id)
                starting_id += len(inst_data_list)  # Increment starting ID
                inst_data_list.clear()

    batch_write(inst_data_list, inst_data_path, starting_id)
    print('Done generating instructions.')
