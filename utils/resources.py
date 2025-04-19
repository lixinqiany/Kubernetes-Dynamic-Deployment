class Pod:
    def __init__(self, request, limit=None):
        self.request = request
        self.limit = limit if limit else request

    @property
    def cpu(self):
        return self.request["CPU"]

    @property
    def memory(self):
        return self.request["RAM"]


class Node:
    def __init__(self, name, configuration, pods=None):
        self.name = name
        self.type = configuration["type"]
        self.cpu = configuration["CPU"]
        self.memory = configuration["RAM"]
        self.price = configuration["price"]
        self.pods = pods if pods else []

    @property
    def available_cpu(self):
        return self.cpu - sum(x.cpu for x in self.pods)

    @property
    def availbale_memory(self):
        return self.memory - sum(x.memory for x in self.pods)

    @property
    def occupied_cpu(self):
        return sum(x.cpu for x in self.pods)

    @property
    def occupied_memory(self):
        return sum(x.memory for x in self.pods)