import argparse
import json
import re

all_steps_with_analysis_format = '''
**Video Details:**
---
- **Video ID**: {Video_id}
- **Raw Description**: 
{raw_description}
- **Contextual Description**: 
{con_description}
- **Analysis**: 
{analysis}
---
'''

step3_format = '''
### Issue Summary (Structured)'''

def getfromid(videoDesList, instance_id):
    for des in videoDesList:
        if des["instance_id"] == instance_id:
            return des

def filter(input_file_path,output_file_path,strlist):
    save_data_list = []
    with open(input_file_path, 'r') as data_file:
        dataList = json.load(data_file)
    for data in dataList:
        if data["instance_id"] in strlist:
            save_data_list.append(data)
    if len(save_data_list) == len(strlist):
        for data in save_data_list:
            print(data["problem_statement"])
        with open(output_file_path,'w',encoding='utf-8') as outfile:
            json.dump(save_data_list, outfile, indent=4)

def add_all_steps_with_analysis(data_file_path,step1_file_path,step2_file_path,step2_analysis_file_path,step3_file_path):
    save_data_list = []
    with open(data_file_path,'r') as data_file, open(step1_file_path,'r',encoding='utf-8') as step1_file, open(step2_file_path,'r',encoding='utf-8') as step2_file, open(step3_file_path,'r',encoding='utf-8') as step3_file, open(step2_analysis_file_path,'r',encoding='utf-8') as step2_analysis_file:
        dataList = json.load(data_file)
        rawVideoDesList = json.load(step1_file)
        VideoDesList = json.load(step2_file)
        VideoAnaList = json.load(step2_analysis_file)
        SummaryList = json.load(step3_file)
    total = 0

    for data in dataList:
        problem_statement = ""
        rawdes = getfromid(rawVideoDesList, data["instance_id"])
        des = getfromid(VideoDesList, data["instance_id"])
        analysis = getfromid(VideoAnaList, data["instance_id"])
        summarydes = getfromid(SummaryList, data["instance_id"])
        index = 0
        for problem in data["problem_statement"]:
            if problem.startswith("http"):
                total += 1
                problem_statement += "This video is part of the problem description. Here is the relevant information:"
                problem_statement += "\n"
                rawdes_value = rawdes["raw_description_list"][index]
                description_value = des["description_list"][index]
                analysis_value = analysis["description_list"][index]
                formatted_output = all_steps_with_analysis_format.format(Video_id=description_value["video_id"],raw_description=rawdes_value,con_description=description_value["description"],analysis=analysis_value["analysis"])
                problem_statement += formatted_output.strip()
                index += 1
            else:
                problem_statement += problem
        problem_statement += step3_format
        for key, value in summarydes["structure_problem"].items():
            problem_statement += f'''\n- **{key}**: {value}'''
        data["problem_statement"] = problem_statement
        save_data_list.append(data)
    with open(f"data_with_video.json", 'w', encoding='utf-8') as outfile:
        json.dump(save_data_list, outfile, indent=4)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Script configuration")
    parser.add_argument("--in_folder", type=str, help="The input folder for results")
    args = parser.parse_args()
    in_folder = args.in_folder
    add_all_steps_with_analysis("Visual SWE-bench/multi_data_onlyvideo.json",f"{in_folder}/step1.json",f"{in_folder}/step2_des.json",f"{in_folder}/step2_analysis.json",f"{in_folder}/step3.json")


