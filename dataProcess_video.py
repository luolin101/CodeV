import argparse
import base64
import json
import os
import re
from openai import OpenAI
from pyarrow.dataset import dataset
from tqdm import tqdm
import os
from dotenv import load_dotenv
# load `.env`
load_dotenv()

SystemPrompt_step1 = '''You are a technical video descriptor. For the given video:

1. If it contains only audio with text, transcribe the text in markdown format.
2. If it contains visual and audio elements:
- Describe the main technical content presented in the video.
- Include specific actions, events, numbers, and text that are visible or audible.
- State the relationships between different elements in the video.
- Focus on technical details over visual or audio aesthetics.

Your description should be detailed enough for an AI model to understand the technical content without seeing the video.'''

SystemPrompt_step2_des = '''You are a technical video descriptor for software issues. Your task is to create detailed descriptions of ALL videos in the issue that will help other AI models understand the issue without seeing the actual videos.

For EACH video in the issue:
1. Read and understand the entire issue context including:
- Bug description
- Code samples
- Error messages
- Expected behavior
- Actual results

2. Create a comprehensive description that:
- Details exactly what is shown in the video
- Connects the video content to the issue context
- Includes any visible technical information that's crucial for understanding the issue
- Provides enough detail that an AI model could understand the issue's visual aspects without seeing the video

Please provide your descriptions in this specific JSON format:
{
  "videos": [
    {
      "video_id": "<sequential number>",
      "description": "<detailed technical description that fully captures the video content and its relationship to the issue>"
    }
  ]
}

CRITICAL: Ensure you describe EVERY video present in the issue - missing any video would make the issue harder to understand for AI models that cannot see the images.
'''

SystemPrompt_step2_analysis = '''You are a specialized technical video analyst for software issues. Your task is to analyze 
how each video connects to and supports the reported issue. Focus on providing a comprehensive analysis that explains 
the video's role and value in the issue context.

For each video, analyze:

1. Direct Issue Connection
    - How does this video specifically demonstrate or relate to the reported issue?
    - What aspects of the issue does this video capture or verify?
    - Why was including this video necessary for documenting this issue?

2. Technical Value
    - What key technical details does this video reveal about the issue?
    - How do specific elements in the video help understand the problem?
    - What insights does this video provide for troubleshooting or resolution?

3. Documentation Importance
    - What unique information does this video convey that text alone couldn't?
    - How does this video strengthen the overall issue documentation?
    - What critical details should developers focus on when reviewing this video?

Provide your analysis in this JSON format: 
{ 
    "videos": [ 
        { 
            "video_id": "<sequential number>", 
            "analysis": "<comprehensive analysis covering the video's connection to the issue, its technical value, and documentation importance. Focus on explaining why this video matters for understanding and resolving the specific issue at hand. Include relevant technical details and their significance to the issue context.>" 
        } 
    ] 
}

Key Guidelines:
- Create a narrative that clearly connects the video to the issue context.
- Focus on why this video is necessary for understanding the specific issue.
- Include relevant technical details and their significance.
- Explain how the video contributes to issue documentation and resolution.
- Be thorough but concise in your analysis.
'''

SystemPrompt_step3 = '''   You are an issue organizer and analyzer. The user will provide you with an issue that includes text descriptions and videos. Your task is to analyze this information thoroughly and output a structured summary of the issue in JSON format.

The output should include relevant elements as applicable, but you are not required to fill in every field if the information is not available or cannot be accurately summarized. Aim to include:

```json
   {
       "problemSummary": "<a concise summary of the problem>",
       "context": "<any relevant background information>",
       "stepsToReproduce": [
           "<step 1: describe the action taken>",
           "<step 2: describe the next action>",
           "...<more steps as necessary>"
       ],
       "expectedResults": "<what the user expected to happen>",
       "actualResults": "<what actually happened>",
       "supplementaryVideos": [
           "<descriptions of the videos provided>"
       ],
       "additionalNotes": "<any other relevant information or notes>"
   }```

Feel free to omit any fields that are not applicable or where information is uncertain, while ensuring the output remains clear and informative to assist other models in understanding and resolving the issue effectively.
'''

def system_message(text):
    message = {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": text
            }
        ]
    }
    return message


def user_message_step1(video_path):
    message = {
        "role": "user",
        "content": [
            {
                "type": "video",
                "video": [
                    f"file:///{video_path}",
                ],
                "fps": 1.0,
            }
        ]
    }
    return message


def user_message_step2(problem_list, video_list):
    contents = []
    for i in range(len(video_list)):
        if video_list[i] == 0:
            contents.append({
                "type": "text",
                "text": problem_list[i]
            })
        elif video_list[i] == 1:
            contents.append({
                "type": "video",
                "video": f"file:///{problem_list[i]}",
                "fps": 1.0,
            })
        else:
            pass
    message = {
        "role": "user",
        "content": contents
    }
    return message

def step1(data_file):
    with open(data_file, "r") as f:
        data_list = json.load(f)
    save_data_list = []
    for data in tqdm(data_list):
        raw_description_list = []
        instance_id = data["instance_id"]
        index = 0
        for problem in data["problem_statement"]:
            if problem.startswith('http'):
                message1 = system_message(SystemPrompt_step1)
                message2 = user_message_step1(f"Visual SWE-bench/Videos/{instance_id}/Video{index}.mp4")
                completion = client.chat.completions.create(
                    model=model,
                    messages=[message1, message2],
                    temperature=0.2
                )
                index += 1
                raw_description_list.append(completion.choices[0].message.content)
            else:
                continue
        save_data_list.append({
            "instance_id": instance_id,
            "raw_description_list": raw_description_list
        })
    with open(f"{out_folder}/step1.json", 'w', encoding='utf-8') as outfile:
        json.dump(save_data_list, outfile, ensure_ascii=False, indent=4)

def step2(data_file, type="des"):
    with open(data_file, "r") as f:
        data_list = json.load(f)
    save_data_list = []
    for data in tqdm(data_list):
        problem_list = []
        video_list = []
        instance_id = data["instance_id"]
        index = 0
        for problem in data["problem_statement"]:
            if problem.startswith('http'):
                problem_list.append(f"Visual SWE-bench/Videos/{instance_id}/Video{index}.mp4")
                video_list.append(1)
                index += 1
            else:
                problem_list.append(problem)
                video_list.append(0)
        message1 = system_message(SystemPrompt_step2_des)
        if type == "analysis":
            message1 = system_message(SystemPrompt_step2_analysis)
        message2 = user_message_step2(problem_list, video_list)
        completion = client.chat.completions.create(
            model=model,
            messages=[message1, message2],
            temperature=0.3
        )
        input_str = completion.choices[0].message.content
        try:
            json_matches = re.findall(r'\{[^{}]*\}', input_str)
            description_list = [json.loads(json_str) for json_str in json_matches]
            save_data_list.append({
                "instance_id": instance_id,
                "description_list": description_list
            })
        except json.decoder.JSONDecodeError as e:
            print(instance_id, f"error,input_str=" + input_str)
    if type == "des":
        with open(f"{out_folder}/step2_des.json", 'w', encoding='utf-8') as outfile:
            json.dump(save_data_list, outfile, ensure_ascii=False, indent=4)
    if type == "analysis":
        with open(f"{out_folder}/step2_analysis.json", 'w', encoding='utf-8') as outfile:
            json.dump(save_data_list, outfile, ensure_ascii=False, indent=4)

def step3(data_file):
    with open(data_file, "r") as f:
        data_list = json.load(f)
    save_data_list = []
    for data in tqdm(data_list):
        problem_list = []
        video_list = []
        instance_id = data["instance_id"]
        index = 0
        for problem in data["problem_statement"]:
            if problem.startswith('http'):
                problem_list.append(f"Visual SWE-bench/Videos/{instance_id}/Video{index}.mp4")
                video_list.append(1)
                index += 1
            else:
                problem_list.append(problem)
                video_list.append(0)

        message1 = system_message(SystemPrompt_step3)
        message2 = user_message_step2(problem_list, video_list)
        completion = client.chat.completions.create(
            model=model,
            messages=[message1, message2]
        )

        input_str = completion.choices[0].message.content
        try:
            structure_problem = json.loads(input_str.strip().split('\n', 1)[1].rsplit('```', 1)[0].strip())
            save_data_list.append({
                "instance_id": instance_id,
                "structure_problem": structure_problem
            })
        except:
            print(instance_id, "error,input_str=" + input_str)
    with open(f"{out_folder}/step3.json", 'w', encoding='utf-8') as outfile:
        json.dump(save_data_list, outfile, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    base_url = os.getenv("base_url")
    api_key = os.getenv("api_key")
    model = os.getenv("model")
    client = OpenAI(
        base_url=base_url,
        api_key=api_key
    )
    parser = argparse.ArgumentParser(description="Script configuration")
    parser.add_argument("--out_folder", type=str, default=model, help="The output folder for results")
    parser.add_argument("--dataset", type=str, default="Visual SWE-bench/list_data_onlyvideo.json")
    args = parser.parse_args()
    out_folder = args.out_folder
    dataset = args.dataset

    step1(dataset)
    step2(dataset,"des")
    step2(dataset,"analysis")
    step3(dataset)
