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
3. Install the dependencies:
    ```sh
    [Insert installation command, e.g., npm install, pip install -r requirements.txt]
    ```

## Usage
To create multi-modal data from Github repositories, follow these steps:

1. collect_comp_seeds.sh
2. batch_data_renderer_run.sh
3. gen_inst.sh

Example:


## Contributing
We welcome contributions from the open-source community to improve Flame’s dataset, model, and evaluation pipeline. If you're interested in contributing, please follow these steps:
1. Fork the repository.
2. Create a new branch for your changes.
3. Submit a pull request with a clear description of your modifications.

## Acknowledgements
This project was inspired by recent advancements in large vision-language models and automated front-end development. We acknowledge the contributions of the open-source community and prior research in vision-language modeling and automated code generation.