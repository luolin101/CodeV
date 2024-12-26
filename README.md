<h1 align="center">
  CodeV: Issue Resolving with Visual Data
</h1>

## 📁 Visual SWE-bench
The dataset under the `Visual SWE-bench` directory:
- `data.json`: Visual SWE-bench dataset following the [SWE-bench](https://huggingface.co/datasets/princeton-nlp/SWE-bench) structure.
- `list_data.json`: Dataset where the `problem_statement` field is a list of strings, each representing a hyperlink to an image, video, or issue text.
- `list_data_onlyimage.json`: A subset of `list_data.json`, where the `problem_statement` contains only visual data consisting of image hyperlinks.
- `list_data_onlyvideo.json`: A subset of `list_data.json`, where the `problem_statement` contains only visual data consisting of video hyperlinks.

## 🚀 Set Up
To build CodeV from source, follow these steps:
```bash
git clone https://github.com/luolin101/CodeV.git
cd CodeV
pip install -e .
```

## 💽 Usage
### Model Set
To configure the visual language model (VLM) used in this project, update the `.env` file with the following settings:
- **`base_url`**: The base URL for the VLM API.
- **`api_key`**: Your API key for authentication.
- **`model`**: The specific model you intend to use.
### Data Process
1.Process Image
```bash
python dataProcess_image.py --dataset "Visual SWE-bench/list_data_onlyimage.json" \
    --out_folder output_folder_iamge
```
This will generate the processed image information under the `output_folder_image` directory.

2.Process Video
```bash
python dataProcess_video.py --dataset "Visual SWE-bench/list_data_onlyvideo.json" \
    --out_folder output_folder_video
```
This will generate the processed video information under the `output_folder_video` directory. 

Note: Given that the VLM may not strictly follow the json format required by prompt when generating responses, and manual adjustment is needed.

### Patch Generation
1.Add Image Information
```bash
python addImage.py --dataset "Visual SWE-bench/list_data_onlyimage.json" \
    --in_folder output_folder_iamge
```
This will generate `data_with_image.json` with the image information appended to the `problem_statement` field.

2.Add Video Information
```bash
python addVideo.py --dataset "Visual SWE-bench/list_data_onlyvideo.json" \
    --in_folder output_folder_video
```
This will generate `data_with_video.json` with the video information appended to the `problem_statement` field.

3.Merge Data
```bash
python mergeData.py --file1 data_with_image.json \
    --file2 data_with_video.json
```
From here, all visual issues have been converted to textual form and saved in `processed_data.json`.

4.Use Textual Issue Resolving Approaches

After  obtaining `processed_data.json`, we can use approaches like [SWE-agent](https://github.com/SWE-agent/SWE-agent), [Agentless](https://github.com/OpenAutoCoder/Agentless), and other textual issue resolving approaches to resolve the issues within the data.

## 📊 Evaluation
Use `visualswebench.harness.run_evaluation` to evaluate your predictions on Visual SWE-bench:
```bash
python -m visualswebench.harness.run_evaluation \
    --dataset_name "Visual SWE-bench/data.json" \
    --predictions_path <path_to_predictions> \
    --max_workers <num_workers> \
    --run_id <run_id>
    # use --predictions_path 'gold' to verify the gold patches
    # use --run_id to name the evaluation run
```

You can also evaluate on specific issue instances:
```bash
python -m visualswebench.harness.run_evaluation \
    --dataset_name "Visual SWE-bench/data.json" \
    --predictions_path <path_to_predictions> \
    --max_workers <num_workers> \
    --run_id <run_id> \
    --instance_ids <instance_id>
```

The outputs include:
- docker build logs under the `build_image_logs` directory
- evaluation logs under the `run_instance_logs` directory
- a result summary in the `<prediction_file_name>.<run_id>.json` file
