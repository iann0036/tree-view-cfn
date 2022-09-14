import boto3
import sys
import json
import re
from cfn_flip import to_json
import argparse


def resolvePaths(template, prop, loop_check, paths, exclusions):
    if isinstance(prop, dict):
        if 'Ref' in prop:
            if prop['Ref'] in template['Resources'].keys() and prop['Ref'] not in exclusions:
                paths += [prop['Ref']]
        elif 'Fn::GetAtt' in prop:
            if prop['Fn::GetAtt'][0] in template['Resources'].keys() and prop['Fn::GetAtt'][0] not in exclusions:
                paths += [prop['GetAtt'][0]]
        elif 'Fn::Sub' in prop:
            substr = prop['Fn::Sub']
            sub_exclusions = exclusions
            if isinstance(prop['Fn::Sub'], list) and not isinstance(prop['Fn::Sub'], str):
                substr = prop['Fn::Sub'][0]
                sub_exclusions += prop['Fn::Sub'][1].keys()
            r1 = re.findall(r"\$\{(\w+)", substr)
            paths = [x for x in r1 if x not in sub_exclusions]
        for v in prop.values():
            paths = resolvePaths(template, v, loop_check, paths, exclusions)
    elif isinstance(prop, list) and not isinstance(prop, str):
        for listitem in prop:
            paths = resolvePaths(template, listitem, loop_check, paths, exclusions)
    
    return paths


def getFullPaths(res_paths, target, current_paths):
    new_paths = []
    for pathitem in res_paths[target]:
        extended_paths = []
        for current_path in current_paths:
            extended_paths.append([pathitem] + current_path)
        new_paths += getFullPaths(res_paths, pathitem, extended_paths)
    
    if len(new_paths) == 0:
        return current_paths

    return new_paths


def generateTemplate(original_template, exclusions):
    template = json.loads(to_json(original_template))

    res_paths = {}
    for k in template['Resources'].keys():
        prop = {}
        if template['Resources'][k].get('Properties') is not None:
            prop = template['Resources'][k]['Properties']
        
        res_paths[k] = resolvePaths(template, prop, [k], [], exclusions + ['AWS'])

    for k in template['Resources'].keys():
        fullpaths = getFullPaths(res_paths, k, [[k]])

        max_length = 999
        selected_path = []
        for fullpath in fullpaths:
            if len(fullpath) < max_length:
                max_length = len(fullpath)
                selected_path = fullpath

        metadata = dict()
        if template['Resources'][k].get('Metadata') is not None:
            metadata.update(template['Resources'][k]['Metadata'])
        metadata.update({
            "aws:cdk:path": "TreeViewCFN/{}/Resource".format('/'.join(selected_path))
        })
        template['Resources'][k]['Metadata'] = metadata

    return json.dumps(template)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Converts templates or stacks to be tree-view compliant')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--filename", help="The filename of a local template you wish to convert, will output to console")
    group.add_argument("--stack", help="The stack name of a remote stack you wish to convert, will update in place")
    parser.add_argument("--region", help="(optional) The region name to use when polling remote stacks")
    parser.add_argument("--profile", help="(optional) The profile name to use when polling remote stacks")
    args = parser.parse_args()
    
    if args.filename is not None:
        file_content = ''
        with open(sys.argv[1]) as f:
            file_content = f.read()

        print(generateTemplate(file_content, []))
    elif args.stack is not None:
        session = boto3.session.Session(profile_name=args.profile)
        cfnclient = session.client('cloudformation', region_name=args.region)

        stacks = []
        try:
            stacks = cfnclient.describe_stacks(
                StackName=args.stack
            )['Stacks']
        except:
            sys.exit('could not find the requested stack')

        if len(stacks) != 1:
            sys.exit('too many returned stacks')

        stack_params = []
        parameter_names = []
        if 'Parameters' in stacks[0]:
            stack_params = stacks[0]['Parameters']
            for stack_param in stack_params:
                parameter_names.append(stack_param['ParameterKey'])

        original_template = ''
        try:
            original_template = cfnclient.get_template(
                StackName=stacks[0]['StackId'],
                TemplateStage='Processed'
            )['TemplateBody']
        except:
            sys.exit('could not retrieve template body')

        if original_template == '':
            sys.exit('could not retrieve template body')

        if not isinstance(original_template, str):
            original_template = json.dumps(original_template)

        updated_template = generateTemplate(original_template, parameter_names)

        cfnclient.update_stack(
            StackName=stacks[0]['StackId'],
            TemplateBody=updated_template,
            Capabilities=[
                'CAPABILITY_NAMED_IAM',
                'CAPABILITY_AUTO_EXPAND'
            ],
            Parameters=stack_params
        )

        waiter = cfnclient.get_waiter('stack_update_complete')
        waiter.wait(
            StackName=stacks[0]['StackId'],
            WaiterConfig={
                'Delay': 2,
                'MaxAttempts': 10
            }
        )

        print("successfully updated stack")
    else:
        raise Exception("unknown options")
