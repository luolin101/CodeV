import base64
import json
import re

from openai import OpenAI
from tqdm import tqdm

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

SystemPrompt_step2 = '''You are a specialized technical video analyst for software issues. Your task is to analyze 
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

Provide your analysis in this JSON format: { "videos": [ { "video_id": "<sequential number>", "analysis": 
"<comprehensive analysis covering the video's connection to the issue, its technical value, and documentation 
importance. Focus on explaining why this video matters for understanding and resolving the specific issue at hand. 
Include relevant technical details and their significance to the issue context.>" } ] }

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


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


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


def user_message_step1():
    message = {
        "role": "user",
        "content": [
            {
                "type": "video",
                "video": [
                    "file:///gemini/platform/public/users/linhao/video/video1.mp4",
                    "file:///gemini/platform/public/users/linhao/video/video2.mp4",
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
                "video": f"{problem_list[i]}",
                "fps": 1.0,
            })
        else:
            pass
    message = {
        "role": "user",
        "content": contents
    }
    return message


client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="token-abc123",  # 随便填写，只是为了通过接口参数校验
)


def step1():
    save_data_list = []
    instance_id = 'matplotlib__matplotlib-25631'
    raw_description_list = []
    message1 = system_message(SystemPrompt_step1)
    message2 = user_message_step1()
    completion = client.chat.completions.create(
        model="/gemini/platform/public/llm/huggingface/Qwen/Qwen2-VL-72B-Instruct",
        messages=[message1, message2],
        temperature=0.2,
        seed=42
    )
    raw_description_list.append(completion.choices[0].message.content)
    save_data_list.append({
        "instance_id": instance_id,
        "raw_description_list": raw_description_list
    })
    with open("step1_video.json", 'w', encoding='utf-8') as outfile:
        json.dump(save_data_list, outfile, ensure_ascii=False, indent=4)


def step2(data_file):
    with open(data_file, "r") as f:
        data_list = json.load(f)
    save_data_list = []
    for data in tqdm(data_list):
        if data["instance_id"] != "matplotlib__matplotlib-25631":
            continue
        problem_list = []
        video_list = []
        instance_id = data["instance_id"]
        index = 1
        for problem in data["problem_statement"]:
            if problem.startswith('http'):
                problem_list.append(f"file:///gemini/platform/public/users/linhao/video/video{index}.mp4")
                video_list.append(1)
                index += 1
            else:
                problem_list.append(problem)
                video_list.append(0)

        message1 = system_message(SystemPrompt_step2)
        message2 = user_message_step2(problem_list, video_list)
        completion = client.chat.completions.create(
            model="/gemini/platform/public/llm/huggingface/Qwen/Qwen2-VL-72B-Instruct",
            messages=[message1, message2],
            temperature=0.3,
            seed=42
        )
        input_str = completion.choices[0].message.content
        # print(instance_id,f"success,input_str=" + input_str)
        try:
            # 使用正则表达式匹配 JSON 结构
            json_matches = re.findall(r'\{[^{}]*\}', input_str)
            # 将提取到的 JSON 字符串转换为 Python 字典，并存入列表
            description_list = [json.loads(json_str) for json_str in json_matches]
            save_data_list.append({
                "instance_id": instance_id,
                "description_list": description_list
            })
        except json.decoder.JSONDecodeError as e:
            # 如果解析失败，捕获JSONDecodeError异常并处理
            print(instance_id, f"error,input_str=" + input_str)
            # 你可以选择在这里记录错误、跳过当前字符串或采取其他措施

    with open("step2_video.json", 'w', encoding='utf-8') as outfile:
        json.dump(save_data_list, outfile, ensure_ascii=False, indent=4)


def step3(data_file):
    with open(data_file, "r") as f:
        data_list = json.load(f)
    save_data_list = []
    for data in tqdm(data_list):
        if data["instance_id"] != "matplotlib__matplotlib-25631":
            continue
        problem_list = []
        video_list = []
        instance_id = data["instance_id"]
        index = 1
        for problem in data["problem_statement"]:
            if problem.startswith('http'):
                problem_list.append(f"file:///gemini/platform/public/users/linhao/video/video{index}.mp4")
                video_list.append(1)
                index += 1
            else:
                problem_list.append(problem)
                video_list.append(0)

        message1 = system_message(SystemPrompt_step3)
        message2 = user_message_step2(problem_list, video_list)
        # print(message2)
        completion = client.chat.completions.create(
            model="/gemini/platform/public/llm/huggingface/Qwen/Qwen2-VL-72B-Instruct",
            messages=[message1, message2],
            #temperature = 0.3,
            # seed = 42
        )

        input_str = completion.choices[0].message.content
        # print(instance_id, "success,inputstr=" + input_str)
        try:
            structure_problem = json.loads(input_str.strip().split('\n', 1)[1].rsplit('```', 1)[0].strip())
            save_data_list.append({
                "instance_id": instance_id,
                "structure_problem": structure_problem
            })
        except:
            print(instance_id, "error,input_str=" + input_str)
    with open("step3_video.json", 'w', encoding='utf-8') as outfile:
        json.dump(save_data_list, outfile, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    step1()
    step2('origin_data.json')
    step3('origin_data.json')
    #step2("test.json")
