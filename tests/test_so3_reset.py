# in tests/test_so3_reset.py
import numpy as np
from python.so3_reset import quat_mul

def test_quat_identity_multiplication():
    """Test that multiplying by the identity quaternion [1,0,0,0] doesn't change anything."""
    q = np.array([0.5, 0.5, 0.5, 0.5])
    identity = np.array([1.0, 0.0, 0.0, 0.0])
    
    result = quat_mul(q, identity)
    
    assert np.allclose(q, result)