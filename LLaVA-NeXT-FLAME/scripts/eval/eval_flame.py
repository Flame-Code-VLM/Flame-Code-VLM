
import ast
import os
import copy
from dataclasses import dataclass, field
import json
import logging
import pathlib
from typing import Dict, Optional, Sequence, List
from PIL import Image, ImageFile
from packaging import version
import numpy as np
import warnings

import argparse 
import traceback
import time
import random
import yaml
import math
import re
import torch

import transformers
import tokenizers
import deepspeed
import jsonlines

import os
os.environ["CRYPTOGRAPHY_OPENSSL_NO_LEGACY"] = "1"

from transformers import AutoConfig
from torch.utils.data import Dataset
from llava.constants import IGNORE_INDEX, DEFAULT_IMAGE_TOKEN, DEFAULT_IM_START_TOKEN, DEFAULT_IM_END_TOKEN, IMAGE_TOKEN_INDEX, PROMPT_DICT
from llava.train.llava_trainer import LLaVATrainer

from llava import conversation as conversation_lib
from llava.model import *
from llava.mm_utils import process_highres_image, process_anyres_image, process_highres_image_crop_split, tokenizer_image_token
from llava.utils import rank0_print, process_video_with_pyav, process_video_with_decord

from llava.model.builder import load_pretrained_model
from torch.utils.data import DataLoader


@dataclass
class DataArguments:
    data_path: str = field(default=None, metadata={"help": "Path to the training data, in llava's instruction.json format. Supporting multiple json files via /path/to/{a,b,c}.json"})
    lazy_preprocess: bool = False
    is_multimodal: bool = False
    early_mix_text: bool = False
    image_folder: Optional[str] = field(default=None)
    image_aspect_ratio: str = "square"
    image_grid_pinpoints: Optional[str] = field(default=None)
    image_crop_resolution: Optional[int] = field(default=None)
    image_split_resolution: Optional[int] = field(default=None)

    video_folder: Optional[str] = field(default=None)
    video_fps: Optional[int] = field(default=1)
    frames_upbound: Optional[int] = field(default=0)
    prompt_ver: Optional[str] = field(default='v0')
    max_new_tokens: Optional[int] = field(default=4096)

def preprocess_flame(
    source_example,
    tokenizer: transformers.PreTrainedTokenizer,
    has_image: bool = False,
    prompt_ver='v0'
) -> Dict:

    if source_example['image'] != "":
        prompt_temp = PROMPT_DICT[prompt_ver]
        prefix = prompt_temp.format_map(dict(instruction=source_example['instruction_requirement'], layout=source_example['instruction_layout'], css_code=source_example['style'], code=source_example['component'], image=DEFAULT_IMAGE_TOKEN))
    else:
        prompt_temp = PROMPT_DICT["prompt_no_input"]
        prefix = prompt_temp.format_map(dict(instruction=source_example['instruction_requirement']))

    # Tokenize the prompt; if the data contains an image, then mark the image_index in the tokenized input_ids 
    if has_image:
        input_ids = tokenizer_image_token(prefix, tokenizer, return_tensors='pt')
    else:
        input_ids = tokenizer(
            prefix,
            return_tensors="pt",
            padding="longest",
            max_length=tokenizer.model_max_length,
            truncation=True,
        ).input_ids[0]  # return a list for ds tokenizer

    return dict(input_ids=input_ids)


class LazySupervisedMMCoderDataset(Dataset):
    def __init__(self, data_path: str, tokenizer: transformers.PreTrainedTokenizer, data_args: DataArguments):
        super(LazySupervisedMMCoderDataset, self).__init__()

        with jsonlines.open(data_path) as reader:
            list_data_dict = list(reader)

        self.list_data_dict = list_data_dict
        self.tokenizer = tokenizer
        self.data_args = data_args

        rank0_print(f"Loaded {len(self.list_data_dict)} samples from {data_path}")
        rank0_print("Formatting inputs...Skip in lazy mode")

    
    def __len__(self):
        return len(self.list_data_dict)

    @property
    def lengths(self):
        length_list = []
        for source_example in self.list_data_dict:
            img_tokens = 128 if source_example['image'] != '' else 0
            length_list.append(len(source_example['instruction'].split()) + img_tokens)
        return length_list

    @property
    def modality_lengths(self):
        length_list = []
        for source_example in self.list_data_dict:
            cur_len = len(source_example['instruction_requirement'].split())
            cur_len = cur_len if source_example['image']!='' else -cur_len
            length_list.append(cur_len)
        return length_list

    def process_image(self, image_file, overwrite_image_aspect_ratio=None):
        image_folder = self.data_args.image_folder
        processor = self.data_args.image_processor
        # print(f"\n\nInspecting the image path, folder = {image_folder}, image={image_file}\n\n")
        try:
            image = Image.open(os.path.join(image_folder, image_file)).convert("RGB")
        except Exception as exn:
            print(f"Failed to open image {image_file}. Exception:", exn)
            raise exn

        image_size = image.size
        image_aspect_ratio = self.data_args.image_aspect_ratio
        if overwrite_image_aspect_ratio is not None:
            image_aspect_ratio = overwrite_image_aspect_ratio
        if image_aspect_ratio == "highres":
            image = process_highres_image(image, self.data_args.image_processor, self.data_args.image_grid_pinpoints)
        elif image_aspect_ratio == "anyres" or "anyres_max" in image_aspect_ratio:
            image = process_anyres_image(image, self.data_args.image_processor, self.data_args.image_grid_pinpoints)
        elif image_aspect_ratio == "crop_split":
            image = process_highres_image_crop_split(image, self.data_args)
        elif image_aspect_ratio == "pad":

            def expand2square(pil_img, background_color):
                width, height = pil_img.size
                if width == height:
                    return pil_img
                elif width > height:
                    result = Image.new(pil_img.mode, (width, width), background_color)
                    result.paste(pil_img, (0, (width - height) // 2))
                    return result
                else:
                    result = Image.new(pil_img.mode, (height, height), background_color)
                    result.paste(pil_img, ((height - width) // 2, 0))
                    return result

            image = expand2square(image, tuple(int(x * 255) for x in processor.image_mean))
            image = processor.preprocess(image, return_tensors="pt")["pixel_values"][0]
        else:
            image = processor.preprocess(image, return_tensors="pt")["pixel_values"][0]
        return image, image_size, "image"

    def __getitem__(self, i) -> Dict[str, torch.Tensor]:
        # TODO: define number of retries somewhere else
        num_base_retries = 3
        num_final_retries = 300

        # try the current sample first
        for attempt_idx in range(num_base_retries):
            try:
                sample = self._get_item(i)
                return sample
            except Exception as e:
                # sleep 1s in case it is a cloud disk issue
                print(f"[Try #{attempt_idx}] Failed to fetch sample {i}. Exception:", e)
                time.sleep(1)

        # try other samples, in case it is file corruption issue
        for attempt_idx in range(num_base_retries):
            try:
                next_index = min(i + 1, len(self.list_data_dict) - 1)
                # sample_idx = random.choice(range(len(self)))
                sample = self._get_item(next_index)
                return sample
            except Exception as e:
                # no need to sleep
                print(f"[Try other #{attempt_idx}] Failed to fetch sample {next_index}. Exception:", e)
                pass

        try:
            sample = self._get_item(i)
            return sample
        except Exception as e:
            raise e

    def _get_item(self, i) -> Dict[str, torch.Tensor]:
        source_example = self.list_data_dict[i] 

        if source_example['image'] != '':
            image_file = self.list_data_dict[i]["image"]
            if type(image_file) is list:
                image = [self.process_image(f) for f in image_file]
                if len(image_file) > 1:
                    image = [self.process_image(f, "pad") for f in image_file]
                    image = [[im[0], im[1], "image"] for im in image]
            else:
                image = [self.process_image(image_file)] 

        source_example = copy.deepcopy(source_example)
        has_image = source_example['image'] != ''
        data_dict = preprocess_flame(source_example, self.tokenizer, has_image=has_image, prompt_ver=self.data_args.prompt_ver)

        # Remove label processing
        if isinstance(i, int):
            data_dict = dict(input_ids=data_dict["input_ids"])

        if "image" in self.list_data_dict[i]:
            data_dict["image"] = image
        elif self.data_args.is_multimodal:
            crop_size = self.data_args.image_processor.crop_size
            data_dict["image"] = [
                (torch.zeros(1, 3, crop_size["height"], crop_size["width"]), (crop_size["width"], crop_size["height"]), "text"),
            ]

        data_dict["problem_id"] = self.list_data_dict[i].get("problem_id", i)

        return data_dict


@dataclass
class DataCollatorForSupervisedDataset(object):
    """Collate examples for supervised fine-tuning."""

    tokenizer: transformers.PreTrainedTokenizer

    def pad_sequence(self, input_ids, batch_first, padding_value):
        if self.tokenizer.padding_side == "left":
            input_ids = [torch.flip(_input_ids, [0]) for _input_ids in input_ids]
        input_ids = torch.nn.utils.rnn.pad_sequence(input_ids, batch_first=batch_first, padding_value=padding_value)
        if self.tokenizer.padding_side == "left":
            input_ids = torch.flip(input_ids, [1])
        return input_ids

    def __call__(self, instances: Sequence[Dict]) -> Dict[str, torch.Tensor]: 
        # input_ids = tuple([instance[key] for instance in instances] for key in ("input_ids")) 
        input_ids = [instance["input_ids"] for instance in instances]
        input_ids = [_input_ids[: self.tokenizer.model_max_length] for _input_ids in input_ids] 
        if self.tokenizer.pad_token_id is None:
             self.tokenizer.pad_token_id = 0 # This gets the best result. Don't know why.
        input_ids = self.pad_sequence(input_ids, batch_first=True, padding_value=self.tokenizer.pad_token_id) 
        # batch = dict(input_ids=input_ids) 
        batch = dict(
            input_ids=input_ids,
            attention_mask=input_ids.ne(self.tokenizer.pad_token_id)
        )

        if "image" in instances[0]:
            images = [instance["image"] for instance in instances]

            batch["image_sizes"] = [im[1] for im_list in images for im in im_list]
            batch["modalities"] = [im[2] for im_list in images for im in im_list]
            images = [im[0] for im_list in images for im in im_list]
            batch["images"] = images

        if "problem_id" in instances[0]:
            batch["problem_id"] = [instance["problem_id"] for instance in instances]

        return batch


def batch_inference(model, tokenizer, dataloader, device: str = "cuda:0", max_new_tokens: int = 4096, do_sample=False, pen=1.05):
    all_outputs = []
    total_time = 0
    batch_count = 0
    
    for batch in dataloader:
        batch_count += 1
        print(f"Processing batch {batch_count}") 

        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device) 
         
        if 'images' in batch:
            images = [img.to(dtype=torch.float16, device=device) for img in batch['images']]
        else:
            images = None
        
        modalities = batch['modalities']

        image_sizes = batch.get('image_sizes')

        start_time = time.time()
        with torch.no_grad():
            try:
                outputs = model.generate(
                    inputs=input_ids,
                    images=images,
                    image_sizes=image_sizes,
                    modalities=modalities,                   # Added this line with the modalities
                    attention_mask=attention_mask,
                    do_sample=do_sample,
                    temperature=0.1,
                    max_new_tokens=max_new_tokens,
                    top_p=0.95,
                    repetition_penalty=pen
                )
            except Exception as e:
                print(f"Error during generation: {e}")
                print(f"Full error: {traceback.format_exc()}")
                continue
        end_time = time.time()
        batch_time = end_time - start_time
        total_time += batch_time

        print(f"Batch {batch_count} processing time: {batch_time:.2f} seconds")

        decoded_outputs = tokenizer.batch_decode(outputs, skip_special_tokens=True)
 
        for i, output in enumerate(decoded_outputs):
            all_outputs.append({
                "id": batch["problem_id"][i],
                "output": output
            })

    average_time = total_time / batch_count if batch_count > 0 else 0
    print(f"\nTotal batches processed: {batch_count}")
    print(f"Average processing time per batch: {average_time:.2f} seconds")
    print(f"Total processing time: {total_time:.2f} seconds")
    print(f"Total batches processed: {batch_count}")
    print(f"Total outputs generated: {len(all_outputs)}")
    return all_outputs


def main():
    warnings.filterwarnings("ignore")

    parser = argparse.ArgumentParser(description="Run inference on a model")
    parser.add_argument("--model_path", type=str, required=True, help="Path to the model")
    parser.add_argument("--output_file", type=str, required=True, help="Path to save the output JSON")
    parser.add_argument("--gpu_id", type=int, required=True, help="GPU ID to use")
    parser.add_argument("--test_data_path", type=str, default="/root/nfs/LLM4CodeBeta/FLAME_MD/datasets/TEST_DATASET/sample.jsonl", help="Path to the test data")
    parser.add_argument("--test_data_img_path", type=str, default="/root/nfs/LLM4CodeBeta/FLAME_MD/datasets/TEST_DATASET/", help="Path to the test data images")
    parser.add_argument("--batch_size", type=int, default=4, help="Batch size for inference")
    parser.add_argument("--prompt_ver", type=str, default="v6", help="prompt version for inference")
    parser.add_argument("--do_sample", type=bool, default=False, help="do_sample for inference")
    parser.add_argument("--max_new_tokens", type=int, default=4096, help="maximum new tokens")
    parser.add_argument("--pen", type=float, default=1.05, help="repetition_penalty")
    
    args = parser.parse_args() 

    print(args) 

    os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu_id)
 
    assert torch.cuda.is_available(), "CUDA is not available"
    print(f"Using GPU: {torch.cuda.current_device()}")

    device = f"cuda:{args.gpu_id}" if torch.cuda.is_available() else "cpu"
    device_map = device
    print(f"................ using GPU {device} ............\n")

    tokenizer, model, image_processor, max_length = load_pretrained_model(args.model_path, None, "flame", device_map=device_map, attn_implementation=None)
    print(tokenizer.padding_side)
    tokenizer.padding_side = "left"
    model = model.to(device)
    model.eval()

    data_args = DataArguments(
        data_path=args.test_data_path,
        lazy_preprocess=True,
        is_multimodal=True,
        image_folder=args.test_data_img_path,
        image_aspect_ratio="anyres_max_9",
        image_grid_pinpoints="(1x1),...,(6x6)",
        image_crop_resolution=None,
        image_split_resolution=None,
        prompt_ver=args.prompt_ver,
        max_new_tokens=args.max_new_tokens
    )
    data_args.image_processor = image_processor

    print(f"-------------data args -------------------\n")
    print(data_args)
    dataset = LazySupervisedMMCoderDataset(tokenizer=tokenizer, data_path=args.test_data_path, data_args=data_args)
    print(f"Total number of samples in dataset: {len(dataset)}")
    data_collator = DataCollatorForSupervisedDataset(tokenizer=tokenizer)

    dataloader = DataLoader(
        dataset, 
        batch_size=args.batch_size, 
        shuffle=False, 
        collate_fn=data_collator
    )
    print(f"Number of batches in dataloader: {len(dataloader)}")
    print(f"Batch size: {args.batch_size}")

    outputs = batch_inference(model, tokenizer, dataloader, device, args.max_new_tokens, args.do_sample, args.pen)

    print(f"Number of outputs generated: {len(outputs)}")

    with open(args.output_file, 'w', encoding='utf-8') as f:
        json.dump(outputs, f, ensure_ascii=False, indent=2)
    
    print(f"Results saved to {args.output_file}")

if __name__ == "__main__":
    main()