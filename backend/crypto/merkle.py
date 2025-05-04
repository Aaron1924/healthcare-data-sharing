import hashlib
import json

class MerkleTree:
    def __init__(self, elements):
        self.elements = elements
        self.tree = self._build_tree()
        
    def _hash(self, data):
        """Hash the data using SHA-256"""
        if isinstance(data, dict) or isinstance(data, list):
            data = json.dumps(data, sort_keys=True)
        if isinstance(data, str):
            data = data.encode('utf-8')
        return hashlib.sha256(data).hexdigest()
    
    def _build_tree(self):
        """Build the Merkle tree from the elements"""
        # Hash the elements
        hashed_elements = [self._hash(e) for e in self.elements]
        
        # Build the tree
        tree = [hashed_elements]
        
        # Continue until we reach the root
        while len(tree[-1]) > 1:
            level = tree[-1]
            next_level = []
            
            # Process pairs of nodes
            for i in range(0, len(level), 2):
                if i + 1 < len(level):
                    # Hash the pair
                    combined = level[i] + level[i + 1]
                    next_level.append(self._hash(combined))
                else:
                    # Odd number of elements, duplicate the last one
                    next_level.append(level[i])
            
            tree.append(next_level)
        
        return tree
    
    def get_root(self):
        """Get the Merkle root"""
        return self.tree[-1][0]
    
    def get_proof(self, index):
        """Get the Merkle proof for an element"""
        if index < 0 or index >= len(self.elements):
            raise ValueError("Index out of range")
        
        proof = []
        for i, level in enumerate(self.tree[:-1]):  # Skip the root level
            is_right = index % 2 == 0
            pair_index = index + 1 if is_right else index - 1
            
            if pair_index < len(level):
                proof.append({
                    'position': 'right' if is_right else 'left',
                    'data': level[pair_index]
                })
            
            # Move to the next level
            index = index // 2
        
        return proof
    
    def verify_proof(self, element, proof, root=None):
        """Verify a Merkle proof"""
        if root is None:
            root = self.get_root()
        
        # Hash the element
        current = self._hash(element)
        
        # Apply each step in the proof
        for step in proof:
            if step['position'] == 'left':
                current = self._hash(step['data'] + current)
            else:
                current = self._hash(current + step['data'])
        
        # Check if we reached the root
        return current == root

def create_root(data):
    """Create a Merkle root from data"""
    if isinstance(data, dict):
        # Convert dictionary to list of key-value pairs
        elements = [{'key': k, 'value': v} for k, v in data.items()]
    elif isinstance(data, list):
        elements = data
    else:
        # Convert to string and use as a single element
        elements = [str(data)]
    
    tree = MerkleTree(elements)
    return tree.get_root()

def create_proofs(data):
    """Create Merkle proofs for all elements in the data"""
    if isinstance(data, dict):
        # Convert dictionary to list of key-value pairs
        elements = [{'key': k, 'value': v} for k, v in data.items()]
    elif isinstance(data, list):
        elements = data
    else:
        # Convert to string and use as a single element
        elements = [str(data)]
    
    tree = MerkleTree(elements)
    proofs = {}
    
    for i, element in enumerate(elements):
        if isinstance(element, dict) and 'key' in element:
            key = element['key']
        else:
            key = str(i)
        
        proofs[key] = tree.get_proof(i)
    
    return proofs, tree.get_root()

def verify_proof(element, proof, root):
    """Verify a Merkle proof"""
    tree = MerkleTree([])  # Empty tree, just for using the verification method
    return tree.verify_proof(element, proof, root)
