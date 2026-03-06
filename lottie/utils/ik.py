from..nvector import NVector


# FABRIK
class Chain:
    def __init__(self, tail, fixed_tail=True, tolerance=0.5, max_iter=8):
        self.joints = [tail.clone()]
        self.fixed_tail = fixed_tail
        self.lengths = []
        self.total_length = 0
        self.tolerance = tolerance
        self.max_iter = max_iter

    def add_joint(self, point):
        length = (point - self.joints[-1]).length
        self.lengths.append(length)
        self.total_length += length
        self.joints.append(point.clone())

    def add_joints(self, head, n):
        delta = head - self.joints[-1]
        self.total_length += delta.length
        segment = delta / n
        seglen = segment.length
        for i in range(n):
            self.lengths.append(seglen)
            self.joints.append(self.joints[-1] + segment)

    def backward(self, target):
        """!
        target -> -> start
        """
        self.joints[-1] = target
        for i in range(len(self.joints)-2, -1, -1):
            r = self.joints[i+1] - self.joints[i]
            l = self.lengths[i] / r.length
            self.joints[i] = self.joints[i+1].lerp(self.joints[i], l)

    def forward(self, target):
        """!
        start -> -> tail
        """
        self.joints[0] = target
        for i in range(0, len(self.joints)-1):
            r = self.joints[i+1] - self.joints[i]
            l = self.lengths[i] / r.length
            self.joints[i+1] = self.joints[i].lerp(self.joints[i+1], l)

    def reach(self, target):
        if not self.fixed_tail:
            self.backward(target)
            return

        distance = (target - self.joints[0]).length
        if distance >= self.total_length:
            for i in range(len(self.joints)-1):
                r = target - self.joints[i]
                l = self.lengths[i] / r.length
                self.joints[i+1] = self.joints[i].lerp(target, l)
            return

        base = self.joints[0]

        distance = (target - self.joints[-1]).length
        n_it = 0
        while distance > self.tolerance and n_it < self.max_iter:
            self.backward(target)
            self.forward(base)
            distance = (target - self.joints[-1]).length
            n_it += 1


class Octopus:
    def __init__(self, master):
        self.chains = {"master": master}
        self.master = master

    @property
    def base(self):
        return self.master.joints[-1]

    def add_chain(self, name):
        ch = Chain(self.base)
        self.chains[name] = ch
        return ch

    def reach(self, target_map):
        centroid = NVector(0, 0)
        for chain, target in target_map.items():
            self.chains[chain].backward(target)
            centroid += self.chains[chain].joints[0]
        centroid /= len(target_map)

        self.master.reach(centroid)

        for chain in target_map.keys():
            self.chains[chain].forward(self.base)
