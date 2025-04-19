class Pod:
    def __init__(self, request, limit=None):
        self.request = request
        self.limit = limit if limit else request

    @property
    def cpu(self):
        return self.request["CPU"]

    @property
    def memory(self):
        return self.request["Memory"]


class Node:
    def __init__(self, name, configuration, pods):
        self.name = name
        self.type = configuration["type"]
        self.cpu = configuration["CPU"]
        self.memory = configuration["RAM"]
        self.pods = pods

    @property
    def get_available_cpu(self):
        return self.cpu - sum(x.cpu for x in self.pods)

    @property
    def get_availbale_memory(self):
        return self.memory - sum(x.memory for x in self.pods)