import sys

def parse_args(args):
    """
    return args, kwargs, flags
    """
    ret_args = []
    ret_kwargs = {}
    ret_flags = set()
    for arg in args:
        if arg.startswith('--') and arg != '--':
            if '=' in arg:
                k, v = arg.split('=')
                k = k[2:] # remove leading '--'
                ret_kwargs[k] = v
            else:
                ret_flags.add(arg[2:])
        else:
            ret_args.append(arg)
    print( ret_args, ret_kwargs, ret_flags)
    return ret_args, ret_kwargs, ret_flags
