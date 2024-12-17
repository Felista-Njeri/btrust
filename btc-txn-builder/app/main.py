# app/main.py

import unittest
import sys
from test_bitcoin_transaction import TestBitcoinTransactionBuilder

def run_tests():
    """Run the test suite"""
    # Create a test loader
    loader = unittest.TestLoader()
    
    # Create a test suite containing our tests
    suite = loader.loadTestsFromTestCase(TestBitcoinTransactionBuilder)
    
    # Create a test runner
    runner = unittest.TextTestRunner(verbosity=2)
    
    # Run the tests
    result = runner.run(suite)
    
    # Return appropriate exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(run_tests())