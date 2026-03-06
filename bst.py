"""
Binary Search Tree (BST) Implementation for Job Skill Portal
Keys: skill names (alphabetically ordered)
Values: list of job IDs + frequency count
"""


class BSTNode:
    """A single node in the Binary Search Tree."""

    def __init__(self, skill, job_id=None):
        self.skill = skill.lower().strip()
        self.job_ids = set()
        if job_id is not None:
            self.job_ids.add(job_id)
        self.frequency = len(self.job_ids)
        self.left = None
        self.right = None

    def add_job(self, job_id):
        """Add a job ID to this skill node."""
        self.job_ids.add(job_id)
        self.frequency = len(self.job_ids)


class BST:
    """Binary Search Tree for indexing skills to jobs."""

    def __init__(self):
        self.root = None
        self.size = 0

    def insert(self, skill, job_id=None):
        """Insert a skill into the BST. If skill exists, add job_id to it."""
        skill = skill.lower().strip()
        if not skill:
            return
        if self.root is None:
            self.root = BSTNode(skill, job_id)
            self.size += 1
        else:
            self._insert_recursive(self.root, skill, job_id)

    def _insert_recursive(self, node, skill, job_id):
        if skill == node.skill:
            if job_id is not None:
                node.add_job(job_id)
            return
        elif skill < node.skill:
            if node.left is None:
                node.left = BSTNode(skill, job_id)
                self.size += 1
            else:
                self._insert_recursive(node.left, skill, job_id)
        else:
            if node.right is None:
                node.right = BSTNode(skill, job_id)
                self.size += 1
            else:
                self._insert_recursive(node.right, skill, job_id)

    def search(self, skill):
        """Search for a skill in the BST. Returns the node or None."""
        skill = skill.lower().strip()
        return self._search_recursive(self.root, skill)

    def _search_recursive(self, node, skill):
        if node is None:
            return None
        if skill == node.skill:
            return node
        elif skill < node.skill:
            return self._search_recursive(node.left, skill)
        else:
            return self._search_recursive(node.right, skill)

    def delete(self, skill):
        """Delete a skill node from the BST."""
        skill = skill.lower().strip()
        self.root = self._delete_recursive(self.root, skill)

    def _delete_recursive(self, node, skill):
        if node is None:
            return None
        if skill < node.skill:
            node.left = self._delete_recursive(node.left, skill)
        elif skill > node.skill:
            node.right = self._delete_recursive(node.right, skill)
        else:
            # Node found
            self.size -= 1
            if node.left is None:
                return node.right
            elif node.right is None:
                return node.left
            # Node has two children — find inorder successor
            successor = self._find_min(node.right)
            node.skill = successor.skill
            node.job_ids = successor.job_ids
            node.frequency = successor.frequency
            node.right = self._delete_recursive(node.right, successor.skill)
        return node

    def _find_min(self, node):
        current = node
        while current.left is not None:
            current = current.left
        return current

    def inorder(self):
        """Inorder traversal (sorted order)."""
        result = []
        self._inorder_recursive(self.root, result)
        return result

    def _inorder_recursive(self, node, result):
        if node is not None:
            self._inorder_recursive(node.left, result)
            result.append({
                'skill': node.skill,
                'frequency': node.frequency,
                'job_count': len(node.job_ids)
            })
            self._inorder_recursive(node.right, result)

    def preorder(self):
        """Preorder traversal."""
        result = []
        self._preorder_recursive(self.root, result)
        return result

    def _preorder_recursive(self, node, result):
        if node is not None:
            result.append({
                'skill': node.skill,
                'frequency': node.frequency,
                'job_count': len(node.job_ids)
            })
            self._preorder_recursive(node.left, result)
            self._preorder_recursive(node.right, result)

    def postorder(self):
        """Postorder traversal."""
        result = []
        self._postorder_recursive(self.root, result)
        return result

    def _postorder_recursive(self, node, result):
        if node is not None:
            self._postorder_recursive(node.left, result)
            self._postorder_recursive(node.right, result)
            result.append({
                'skill': node.skill,
                'frequency': node.frequency,
                'job_count': len(node.job_ids)
            })

    def to_dict(self, max_depth=None):
        """Export tree as nested dict for D3.js visualization."""
        return self._to_dict_recursive(self.root, 0, max_depth)

    def _to_dict_recursive(self, node, depth, max_depth):
        if node is None:
            return None
        if max_depth is not None and depth >= max_depth:
            has_children = node.left is not None or node.right is not None
            return {
                'name': node.skill,
                'frequency': node.frequency,
                'job_count': len(node.job_ids),
                'depth': depth,
                'truncated': has_children
            }
        result = {
            'name': node.skill,
            'frequency': node.frequency,
            'job_count': len(node.job_ids),
            'depth': depth,
            'truncated': False
        }
        children = []
        left = self._to_dict_recursive(node.left, depth + 1, max_depth)
        right = self._to_dict_recursive(node.right, depth + 1, max_depth)
        if left:
            left['position'] = 'left'
            children.append(left)
        if right:
            right['position'] = 'right'
            children.append(right)
        if children:
            result['children'] = children
        return result

    def get_height(self):
        """Get the height of the BST."""
        return self._height_recursive(self.root)

    def _height_recursive(self, node):
        if node is None:
            return 0
        return 1 + max(self._height_recursive(node.left),
                       self._height_recursive(node.right))

    def get_stats(self):
        """Get BST statistics."""
        return {
            'total_nodes': self.size,
            'height': self.get_height(),
            'is_balanced': self._is_balanced(self.root)
        }

    def _is_balanced(self, node):
        if node is None:
            return True
        left_h = self._height_recursive(node.left)
        right_h = self._height_recursive(node.right)
        if abs(left_h - right_h) <= 1 and \
           self._is_balanced(node.left) and \
           self._is_balanced(node.right):
            return True
        return False

    def get_top_skills(self, n=20):
        """Get top N skills by frequency."""
        all_skills = self.inorder()
        sorted_skills = sorted(all_skills, key=lambda x: x['frequency'], reverse=True)
        return sorted_skills[:n]

    def search_path(self, skill):
        """Return the path taken to search for a skill (for visualization)."""
        skill = skill.lower().strip()
        path = []
        self._search_path_recursive(self.root, skill, path)
        return path

    def _search_path_recursive(self, node, skill, path):
        if node is None:
            return False
        path.append({
            'skill': node.skill,
            'frequency': node.frequency,
            'direction': 'found' if skill == node.skill else ('left' if skill < node.skill else 'right')
        })
        if skill == node.skill:
            return True
        elif skill < node.skill:
            return self._search_path_recursive(node.left, skill, path)
        else:
            return self._search_path_recursive(node.right, skill, path)
