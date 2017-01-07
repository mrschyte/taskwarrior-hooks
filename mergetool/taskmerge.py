import subprocess
import time
import json
import sys
import pprint
import functools

def load(path):
    p = subprocess.Popen(['task', 'rc.data.location={}'.format(path), 'export'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out, err = p.communicate()

    if p.returncode != 0:
        raise 'Error running command'

    return json.loads(out.decode('utf-8'))

def save(path, data):
    p = subprocess.Popen(['task', 'rc.data.location={}'.format(path), 'import'],
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    out, err = p.communicate(input=json.dumps(data).encode('utf-8'))
    sys.stdout.buffer.write(out)

    if p.returncode != 0:
        raise 'Error running command'

def identity(*args):
    if len(args) == 1:
        return args[0]
    return args

def unique(xs, key=identity):
    seen = set()
    return [x for x in xs if not
            (key(x) in seen or seen.add(key(x)))]

def parsetime(s):
    return time.strptime(s, '%Y%m%dT%H%M%SZ')

def mergetask(t1, t2):
    time1 = parsetime(t1['modified'])
    time2 = parsetime(t2['modified'])

    assert time1 < time2

    if 'annotations' in t2:
        if 'annotations' not in t1:
            t1['annotations'] = []
        t1['annotations'].extend(t2['annotations'])

    if t2['status'] == 'completed':
        t1['status'] = 'completed'
        t1['urgency'] = 0

    return t1

def mergeall(tasks):
    if len(tasks) == 0:
        return None
    
    if len(tasks) == 1:
        return list(tasks.values())[0]

    res = [functools.reduce(mergetask, value[1:], value[0])
            for value in tasks.values()]
    return res
    
def merge(local, remote, merged):
    export = load(local) + load(remote)
    tasks = {}

    for task in sorted(export, key=lambda task: parsetime(task['modified'])):
        if task['uuid'] not in tasks:
            tasks[task['uuid']] = []

        tasks[task['uuid']].append(task)

    pprint.pprint(tasks)
    save(merged, mergeall(tasks))

def load(path):
    p = subprocess.Popen(['task', 'rc.data.location={}'.format(path), 'export'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out, err = p.communicate()

    if p.returncode != 0:
        raise 'Error running command'

    return json.loads(out.decode('utf-8'))

def save(path, data):
    p = subprocess.Popen(['task', 'rc.data.location={}'.format(path), 'import'],
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    out, err = p.communicate(input=json.dumps(data).encode('utf-8'))
    sys.stdout.buffer.write(out)

    if p.returncode != 0:
        raise 'Error running command'

merge(sys.argv[1], sys.argv[2], sys.argv[3])
