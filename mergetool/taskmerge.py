import subprocess
import time
import json
import functools
import argparse

from colorama import init, Fore, Back, Style

class TaskWarriorException(Exception):
    def __init__(self, ret, out, err):
        self.ret = ret
        self.out = out
        self.err = err

    def __str__(self):
        return 'Command failed with error {}'.format(self.ret)

class Task(object):
    def __init__(self, dsrc, data):
        self.dsrc = dsrc
        self.data = data

    def __lt__(self, other):
        return self.modified() < other.modified()

    def __repr__(self):
        return repr(self.data)

    def annotations(self):
        if 'annotations' not in self.data:
            return []
        return self.data['annotations']

    def set_annotations(self, annotations):
        self.data['annotations'] = annotations

    def status(self):
        return self.data['status']

    def set_status(self, status):
        self.data['status'] = status

    def urgency(self):
        return self.data['urgency']

    def set_urgency(self, urgency):
        self.data['urgency'] = urgency

    def modified(self):
        def parsetime(s):
            return time.strptime(s, '%Y%m%dT%H%M%SZ')
        return parsetime(self.data['modified'])

    def merge(self, other):
        if self.modified() > other.modified():
            return other.merge(self)
        
        if self.dsrc == other.dsrc:
            return other
        else:
            other.set_annotations(unique(self.annotations() + other.annotations(), sort=True,
                                         key=lambda ann: ann['description']))

            if self.status() == 'completed':
                other.set_status('completed')
                other.set_urgency(0)

            return other

def identity(*args):
    if len(args) == 1:
        return args[0]
    return args

def unique(xs, sort=False, key=identity):
    if sort:
        items = sorted(xs, key=key)
    else:
        items = xs

    seen = set()
    return [x for x in items if not
            (key(x) in seen or seen.add(key(x)))]

class Database(object):
    def __init__(self, path):
        self.path = path
        self.tasks = self.load()
        
    def load(self):
        p = subprocess.Popen(['task', 'rc.data.location={}'.format(self.path), 'export'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, err = p.communicate()

        if p.returncode != 0:
            raise TaskWarriorException(p.returncode, out, err)

        self.data = [Task(self, task) for task in json.loads(out.decode('utf-8'))]
        return out, err

    def save(self):
        p = subprocess.Popen(['task', 'rc.data.location={}'.format(self.path), 'import'],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        data = json.dumps([task.data for task in self.data])
        out, err = p.communicate(input=data.encode('utf-8'))

        if p.returncode != 0:
            raise TaskWarriorException(p.returncode, out, err)

        return out, err

    def merge(self, other):
        export = self.data + other.data
        tasks = {}

        for task in sorted(export):
            if task.data['uuid'] not in tasks:
                tasks[task.data['uuid']] = []

            tasks[task.data['uuid']].append(task)

        if len(tasks) == 0:
            self.data = []
        elif len(tasks) == 1:
            self.data = list(tasks.values())[0]
        else:
            self.data = [functools.reduce(lambda task, other: task.merge(other),
                                          value[1:], value[0])
                         for value in tasks.values()]

def do_merge(local, remote):
    local = Database(local)
    remote = Database(remote)

    local.merge(remote)
    out, err = local.save()

    print(Fore.CYAN + out.decode('utf-8') + Style.RESET_ALL)
    print(Fore.RED + err.decode('utf-8') + Style.RESET_ALL)

def __main__():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("local")
    parser.add_argument("remote")
    args = parser.parse_args()

    do_merge(args.local, args.remote)

if __name__ == "__main__":
    init()

    try:
        __main__()
    except TaskWarriorException as ex:
        print(Fore.CYAN + ex.out + Style.RESET_ALL)
        print(Fore.RED + ex.err + Style.RESET_ALL)
