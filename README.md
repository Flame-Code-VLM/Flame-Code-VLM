# Flame: a large vision language model for front-end code generation

- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)

## Introduction
Flame is an open-source large vision-language model (VLM) designed for front-end code generation. It aims to bridge the gap between UI design mockups and executable front-end code by leveraging multimodal learning techniques. This repository contains the full implementation of Flame’s data preparation pipeline, training procedure, and evaluation pipeline, as described in our research paper. Through a combination of automated data synthesis, self-reflective training, and benchmarking, Flame achieves state-of-the-art performance in vision-to-code tasks, particularly for React-based development.

## Features
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

### Training

### Evaluation

## Contributing
We welcome contributions from the open-source community to improve Flame’s dataset, model, and evaluation pipeline. If you're interested in contributing, please follow these steps:
1. Fork the repository.
2. Create a new branch for your changes.
3. Submit a pull request with a clear description of your modifications.

## License
Flame is released under the Apache 2.0 License. See the [LICENSE](LICENSE) file for more details.

## Acknowledgements
This project was inspired by recent advancements in large vision-language models and automated front-end development. We acknowledge the contributions of the open-source community and prior research in vision-language modeling and automated code generation.