from typing import List, Dict
import hashlib
import ecdsa
import struct

class UTXO:
    def __init__(self, txid: str, vout: int, amount: int, script_pubkey: str):
        self.txid = txid
        self.vout = vout
        self.amount = amount  # in satoshis
        self.script_pubkey = script_pubkey

class TransactionInput:
    def __init__(self, utxo: UTXO):
        self.txid = utxo.txid
        self.vout = utxo.vout
        self.script_sig = None
        self.witness = None
        self.sequence = 0xffffffff

class TransactionOutput:
    def __init__(self, amount: int, script_pubkey: str):
        self.amount = amount
        self.script_pubkey = script_pubkey

class BitcoinTransactionBuilder:
    def __init__(self):
        self.inputs: List[TransactionInput] = []
        self.outputs: List[TransactionOutput] = []
        self.fee_rate = 1  # satoshis per vbyte
        self.change_address = None
    
    def select_utxos(self, available_utxos: List[UTXO], target_amount: int) -> List[UTXO]:
        """
        Implement coin selection algorithm
        Uses a simple algorithm that keeps selecting UTXOs until we have enough funds
        """
        selected_utxos = []
        total_amount = 0
        
        # Sort UTXOs by amount in descending order for efficiency
        sorted_utxos = sorted(available_utxos, key=lambda u: u.amount, reverse=True)
        
        # Keep selecting UTXOs until we have enough or run out
        for utxo in sorted_utxos:
            selected_utxos.append(utxo)
            total_amount += utxo.amount
            
            # Break if we have enough funds
            if total_amount >= target_amount:
                break
        
        # If we don't have enough funds after selecting all UTXOs, raise an error
        if total_amount < target_amount:
            raise ValueError(f"Insufficient funds: have {total_amount}, need {target_amount}")
        
        return selected_utxos
    
    def add_input(self, utxo: UTXO) -> None:
        """Add an input to the transaction"""
        self.inputs.append(TransactionInput(utxo))
    
    def add_output(self, amount: int, script_pubkey: str) -> None:
        """Add an output to the transaction"""
        self.outputs.append(TransactionOutput(amount, script_pubkey))
    
    def calculate_fee(self) -> int:
        """Calculate the transaction fee based on estimated size"""
        # Rough size estimation
        estimated_vsize = (
            # Basic transaction overhead
            10 +  
            # Input size (compressed pubkey): ~68 vbytes each
            len(self.inputs) * 68 +
            # Output size: ~34 vbytes each
            len(self.outputs) * 34
        )
        
        return estimated_vsize * self.fee_rate
    
    def add_change_output(self, input_amount: int, output_amount: int, fee: int) -> None:
        """Add a change output if necessary"""
        change_amount = input_amount - output_amount - fee
        
        # Check if change amount is above dust threshold (546 satoshis)
        if change_amount >= 546 and self.change_address:
            self.add_output(change_amount, self.change_address)
    
    def sign_input(self, input_index: int, private_key: bytes, sig_hash_type: int = 0x01) -> None:
        """Sign a specific input"""
        # Create signature hash
        sig_hash = self.create_signature_hash(input_index, sig_hash_type)
        
        # Sign using ECDSA
        signing_key = ecdsa.SigningKey.from_string(private_key, curve=ecdsa.SECP256k1)
        signature = signing_key.sign_digest(sig_hash, sigencode=ecdsa.util.sigencode_der)
        
        # Add sighash type
        signature = signature + bytes([sig_hash_type])
        
        # Create script sig (simplified P2PKH)
        public_key = signing_key.get_verifying_key().to_string()
        self.inputs[input_index].script_sig = (
            len(signature).to_bytes(1, 'little') +
            signature +
            len(public_key).to_bytes(1, 'little') +
            public_key
        )
    
    def create_signature_hash(self, input_index: int, sig_hash_type: int) -> bytes:
        """Create a signature hash for signing (simplified)"""
        data_to_sign = (
            struct.pack("<I", 1) +  # version
            len(self.inputs).to_bytes(1, 'little') +
            self.inputs[input_index].txid.encode() +
            struct.pack("<I", self.inputs[input_index].vout) +
            len(self.outputs).to_bytes(1, 'little')
        )
        
        return hashlib.sha256(hashlib.sha256(data_to_sign).digest()).digest()
    
    def build(self) -> dict:
        """Build the final transaction"""
        return {
            "version": 1,
            "inputs": [{
                "txid": input.txid,
                "vout": input.vout,
                "script_sig": input.script_sig.hex() if input.script_sig else "",
                "sequence": input.sequence
            } for input in self.inputs],
            "outputs": [{
                "amount": output.amount,
                "script_pubkey": output.script_pubkey
            } for output in self.outputs],
            "locktime": 0
        }