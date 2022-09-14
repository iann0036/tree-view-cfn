# TreeViewCFN

Force CloudFormation to generate a tree view for any stack.

![](https://raw.githubusercontent.com/iann0036/iann0036/master/static/treeview.png)

> **Warning**
> This script will convert your templates to JSON. You should ensure you have a source template backup if using YAML.

## Usage

To convert a local file and output the result to console:

```
python3 convert.py --filename mystack.yaml
```

Or, to convert a deployed CloudFormation stack:

```
python3 convert.py --stack MyStack
```

### Options

```
usage: convert.py [-h] (--filename FILENAME | --stack STACK) [--region REGION] [--profile PROFILE]

Converts templates or stacks to be tree-view compliant

optional arguments:
  -h, --help           show this help message and exit
  --filename FILENAME  The filename of a local template you wish to convert, will output to console
  --stack STACK        The stack name of a remote stack you wish to convert, will update in place
  --region REGION      (optional) The region name to use when polling remote stacks
  --profile PROFILE    (optional) The profile name to use when polling remote stacks
```
