import unittest
from typing import List
import hashlib
import ecdsa
from bitcoin_transaction_builder import (
    UTXO, 
    BitcoinTransactionBuilder, 
    TransactionInput, 
    TransactionOutput
)

class TestBitcoinTransactionBuilder(unittest.TestCase):
    def setUp(self):
        # Create a test private key
        self.private_key = hashlib.sha256(b'test_key').digest()
        self.signing_key = ecdsa.SigningKey.from_string(self.private_key, curve=ecdsa.SECP256k1)
        self.public_key = self.signing_key.get_verifying_key().to_string()
        
        # Create test UTXOs
        self.test_utxos = [
            UTXO(
                txid="abc123def456",
                vout=0,
                amount=100000,  # 0.001 BTC
                script_pubkey="76a914" + hashlib.sha256(b'test_address1').hexdigest()[:40]
            ),
            UTXO(
                txid="def456abc123",
                vout=1,
                amount=200000,  # 0.002 BTC
                script_pubkey="76a914" + hashlib.sha256(b'test_address2').hexdigest()[:40]
            )
        ]
        
        self.builder = BitcoinTransactionBuilder()
        self.builder.change_address = "76a914" + hashlib.sha256(b'change_address').hexdigest()[:40]

    def test_utxo_selection(self):
        """Test UTXO selection functionality"""
        # Test selecting UTXOs for different amounts
        test_cases = [
            (50000, 1),   # Should select first UTXO
            (150000, 2),  # Should select both UTXOs
        ]
        
        for target_amount, expected_count in test_cases:
            selected = self.builder.select_utxos(self.test_utxos, target_amount)
            self.assertEqual(len(selected), expected_count)
            self.assertGreaterEqual(sum(u.amount for u in selected), target_amount)

    def test_fee_calculation(self):
        """Test transaction fee calculation"""
        # Add some inputs and outputs
        self.builder.add_input(self.test_utxos[0])
        self.builder.add_output(50000, "76a914test")
        
        # Calculate fee
        fee = self.builder.calculate_fee()
        
        # Fee should be proportional to transaction size
        # Basic transaction (~150 vbytes) * fee_rate (1 sat/vbyte)
        self.assertGreater(fee, 100)  # Should be at least 100 satoshis
        self.assertLess(fee, 1000)    # Should be less than 1000 satoshis

    def test_change_output(self):
        """Test change output creation"""
        input_amount = 100000
        output_amount = 60000
        fee = 1000
        
        self.builder.add_change_output(input_amount, output_amount, fee)
        
        # Should create change output if amount is above dust threshold
        self.assertEqual(len(self.builder.outputs), 1)
        self.assertEqual(self.builder.outputs[0].amount, input_amount - output_amount - fee)

    def test_transaction_signing(self):
        """Test transaction signing"""
        # Add input and output
        self.builder.add_input(self.test_utxos[0])
        self.builder.add_output(50000, "76a914test")
        
        # Sign input
        self.builder.sign_input(0, self.private_key)
        
        # Verify signature exists
        self.assertIsNotNone(self.builder.inputs[0].script_sig)
        
        # Basic signature format check
        script_sig = self.builder.inputs[0].script_sig
        self.assertGreater(len(script_sig), 70)  # DER signature + pubkey should be > 70 bytes

    def test_complete_transaction_build(self):
        """Test complete transaction building process"""
        # Create a complete transaction
        recipient_script = "76a914" + hashlib.sha256(b'recipient').hexdigest()[:40]
        
        # Add input
        self.builder.add_input(self.test_utxos[0])
        
        # Add output
        self.builder.add_output(50000, recipient_script)
        
        # Calculate fee and add change
        fee = self.builder.calculate_fee()
        self.builder.add_change_output(100000, 50000, fee)
        
        # Sign input
        self.builder.sign_input(0, self.private_key)
        
        # Build transaction
        tx = self.builder.build()
        
        # Verify transaction structure
        self.assertEqual(tx['version'], 1)
        self.assertEqual(len(tx['inputs']), 1)
        self.assertGreaterEqual(len(tx['outputs']), 1)
        self.assertEqual(tx['locktime'], 0)

    def test_dust_threshold(self):
        """Test dust threshold handling"""
        input_amount = 1000
        output_amount = 500
        fee = 400
        
        self.builder.add_change_output(input_amount, output_amount, fee)
        
        # Should not create change output if amount would be below dust threshold
        self.assertEqual(len(self.builder.outputs), 0)

    def test_insufficient_funds(self):
        """Test handling of insufficient funds"""
        with self.assertRaises(ValueError):
            self.builder.select_utxos(self.test_utxos, 1000000)  # Amount larger than available UTXOs

if __name__ == '__main__':
    unittest.main()