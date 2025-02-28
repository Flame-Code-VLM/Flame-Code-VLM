<h1 align="center">Flame: Advancing vision-language models in front-end development via data synthesis</h1>
<div align="center" style="line-height: 1;">
  <a href="https://huggingface.co/Flame-Code-VLM" target="_blank" style="margin: 2px;">
    <img alt="Datasets" src="https://img.shields.io/badge/%F0%9F%A4%97%20Datasets-Flame%20Code%20VLM-ffc107?color=ffc107&logoColor=white" style="display: inline-block; vertical-align: middle;"/>
  </a>
</div>
<p align="center">
  <a href="README.md">English</a> | <a href="README_zh.md">中文</a>
</p>

- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Dataset](#dataset)
- [Model](#model)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)

## Introduction
State-of-the-art models like GPT-4o, while powerful in generating code for webpage creation, fall short in meeting the dynamic requirements of modern front-end (FE) workflows. The code they generate is often static, lacking essential features like modularity, reusability, and dynamic behavior, which are critical for building scalable, interactive user interfaces. This leads to inefficient and incompatible code that deviates from best development practices.

To overcome these limitations, we introduce a comprehensive framework that includes a data synthesis pipeline, model training process, and evaluation suite, forming a fully integrated vision-language model (VLM) solution for front-end code generation. Using this framework, we developed Flame, a front-end language assistant with multimodal expertise, by integrating the Siglip Vision encoder and the Deepseek coder model for React code generation.

One of the primary challenges in developing a robust large-scale VLM for front-end development is the lack of high-quality image-text data. To address this, we propose an automated data synthesis pipeline that extracts, renders, and annotates self-contained front-end code snippets. This pipeline ensures the generation of large, diverse, and high-fidelity datasets, capable of producing both single-image and multi-image inputs, along with detailed image descriptions for improving visual chain-of-thought (CoT) reasoning. In this process, we leverage DeepSeek's API to integrate both the DeepSeek V2 and V3 models for dataset construction.

To evaluate Flame’s performance, we have established a comprehensive evaluation suite that measures three key factors: syntactic precision, functional correctness, and visual consistency in the generated code. This ensures that Flame generates code that aligns with real-world development standards.

Currently, the framework is designed and optimized for React-based development, taking advantage of its component-based architecture to produce structured, reusable UI components. However, the methodology and pipeline are highly extensible and can be adapted to other front-end frameworks, such as Vue and Angular, with minimal modifications.

This repository provides the full implementation of Flame’s data preparation pipeline, model training process, and evaluation suite, making it an invaluable resource for advancing multimodal front-end code generation research.

## Features

![image not found](./assets/data-pipeline-augmentation.png)

- Comprehensive Data Preparation Pipeline: The repository includes scripts and tools for extracting, synthesizing, and structuring multimodal datasets using three distinct data synthesis methods:
    - Evolution-Based Synthesis
    - Waterfall-Model-Based Synthesis
    - Additive Development Synthesis
- End-to-End Training Pipeline: Implementation of Flame’s three-stage training strategy, incorporating:
    - Vision encoder pretraining with public datasets
    - Image layout interpretation training with synthesized datasets
    - Full instruction-tuning for image-to-code generation
- Evaluation Pipeline for React Code Generation: The repository provides:
    - The Flame-React-Eval benchmarking dataset
    - Automated testing scripts for functional correctness and visual fidelity evaluation
    - Implementation of pass@k evaluation metrics using cosine similarity of rendered outputs
Support for Multi-Image Inputs: The model and pipeline enable iterative UI refinement by processing multiple versions of design mockups and updating generated code accordingly.

This repository provides all necessary scripts, models, and evaluation tools to reproduce our experiments and extend Flame for further research in multimodal front-end code generation.

## Installation
To install, follow these steps:

1. Clone the repository:
    ```sh
    git clone 
    ```
2. Navigate to the project directory:
    ```sh
    cd Flame
    ```
3. Create conda environment:
    ```sh
    conda env create -f environment.yml
    conda activate flame
    ```
4. Install the node dependencies:
    ```sh
    npm install
    ```

## Usage

### Data Preparation
There are 3 main steps in the data preparation pipeline:

#### 1. Generating self-contained component code snippets

To generate self-contained component code snippets from the repositories on Github, you can run the following command:

```sh
bash scripts/collect_gh_code_run.sh
```

Within the _collect_gh_code.sh_ script, there are 3 steps to collect the repositories, extract the components, and extract the images used in the code, respectively. You can specify the parameters in the script according to your needs:

```sh
echo "Step 1: Collecting repositories..."
python3 -B data_collect/repo_collector/collect_info.py \
  --language 'target language' \
  --start_date 'target starting date in the format "YYYY-MM-DD"' \
  --end_date 'target ending date in the format "YYYY-MM-DD"' \
  --per_page 'N repos to clone in one page by GitHub API' \
  --sleep_time 'sleep time between each request to GitHub API' \
  --star 'min stars of the target repo' \
  --time_range 'time range' \
  --kw 'keyword' \
  --output_repo_path 'output dir to store repos' &

echo "Step 2: Collecting components..."
python3 -B data_collect/component_collector/distiller/distiller_cls.py \
  --threads 'N' \
  --repo_path 'dir of the downloaded repos' \
  --output_path 'output dir to store the generated self-contained component code snippets' &

echo "Step 3: Extracting images used in code..."
node data_collect/component_collector/distiller/img_distiller.js \
  'dir of the downloaded repos' \
  'dir of the component code snippets of the downloaded repos' &
```

#### 2. Rendering code snippets to images

To render the code snippets to images, you can first specify the parameters:

```sh
CODE_DIR='dir of the component code snippets of the downloaded repos'
SCREENSHOT_DIR="output dir to store the rendered images"
```

then run the following command:

```sh
bash scripts/renderer_run.sh
```

#### 3. Generating instructions for code snippets

To generate instructions for the code snippets, you can first specify the parameters:

```sh
INST_PATH="output dir to store the final multimodal data"
nohup python -B -u data_collect/component_collector/describer/gen_inst.py \
  --screenshot_path 'dir of the rendered images' \
  --code_path 'dir of the component code snippets of the downloaded repos' \
  --inst_path $INST_PATH \
  --ori_img_path $INST_PATH/ori_images \
  --cropped_img_path $INST_PATH/cropped_images >log/batch_inst.log 2>&1 &
```

then run the following command:

```sh
bash scripts/gen_inst.sh
```

#### Data Synthesis

To synthesize the data with the waterfall-model-based method, you can first specify the parameters in the _run_batch_variation_no_code.sh_ script:

```sh
nohup python3 -B -u data_collect/component_collector/variater/variation_waterfall_no_code.py \
    --iter_num='# of times to iterate the whole engineering process' \
    --max_system_infer='# of systems to infer in the beginning' \
    --screenshot_path='dir of the screenshots of the collected component code snippets' \
    --repo_path='dir of the collected repos' \
    --variation_path='output dir to save the systhesized code snippets'>log/comp_variation_waterfall.log 2>&1 &
```

then run the following command:

```sh
bash scripts/run_batch_variation_no_code.sh
```

To synthesize the data with the additive development method, you can first specify the parameters in the _run_batch_variation_with_code.sh_ script:

```sh
nohup python3 -B -u data_collect/component_collector/variater/variation_waterfall_with_init_code.py \
    --iter_num='# of times to iterate the whole engineering process' \
    --screenshot_path='dir of the screenshots of the collected component code snippets' \
    --repo_path='dir of the collected repos' \
    --variation_path='output dir to save the systhesized code snippets'>log/comp_variation_waterfall_with_init_code.log 2>&1 &
```

then run the following command:

```sh
bash scripts/run_batch_variation_with_code.sh
```

### Modeling & Training 
We build Flame by connecting the Siglip Vision Encoder and the deepseek-coder models with a 2-layer MLP. This repository includes a modified version of the modeling implementation (Flame-Code-VLM/model) based on LLaVA-VL/LLaVA-NeXT [https://github.com/LLaVA-VL/LLaVA-NeXT](https://github.com/LLaVA-VL/LLaVA-NeXT). To use it, simply replace the corresponding code files in the original repository with those from this repo.

### Evaluation
To evaluate the model, you can first generate codes with the model using the following command:

After the code generation, you can then render those code and get the screenshots by first specify the parameters in the _batch_eval_renderer.sh_ script:
```sh
GEN_CODE_DIR="<DIR_OF_GENERATED_CODE>"
SCREENSHOT_DIR="<DIR_TO_SAVE_SCREENSHOTS>"
```

Then run the following command:
```sh
bash scripts/batch_eval_renderer_run.sh
```

Finally, get the pass@k score by first add your model names in _eval_score.sh_:
```sh
MODEL_NAMES=("name of models to evaluate")
```
Then run:
```sh
bash scripts/eval_score_run.sh
```

## Dataset
We have opensourced our datasets constructed with our data collection and synthesis methods, as well as our test dataset used for evaluation:
- Flame-Waterfall-React: <https://huggingface.co/datasets/Flame-Code-VLM/Flame-Waterfall-React>
- Flame-Additive-React: <https://huggingface.co/datasets/Flame-Code-VLM/Flame-Additive-React>
- Flame-Evo-React: <https://huggingface.co/datasets/Flame-Code-VLM/Flame-Evo-React>
- Flame-Eval-React: <https://huggingface.co/datasets/Flame-Code-VLM/Flame-Eval-React>

## Model
- Flame_waterfall_7b: <https://huggingface.co/Flame-Code-VLM/flame_waterfall_7b>
- Llava-qwen2-7b-ov-flamewaterfall: <https://huggingface.co/Flame-Code-VLM/llava-qwen2-7b-ov-flamewaterfall>

## Contributing
We welcome contributions from the open-source community to improve Flame’s dataset, model, and evaluation pipeline. If you're interested in contributing, please follow these steps:
1. Fork the repository.
2. Create a new branch for your changes.
3. Submit a pull request with a clear description of your modifications.

## License
Flame is released under the Apache 2.0 License. See the [LICENSE](LICENSE) file for more details.

## Acknowledgements
This project was inspired by recent advancements in large vision-language models and automated front-end development. We acknowledge the contributions of the open-source community and prior research in vision-language modeling and automated code generation.


