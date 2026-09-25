# ExampleVault - contracts/vault.py (currently deployed, post-audit change)

This is a demo source snapshot for the [AuditScope](https://github.com/HarrisonJL/auditscope) Intelligent Contract - not a real contract.

```
class ExampleVault(gl.Contract):
    owner: Address
    balance: u256

    def __init__(self) -> None:
        self.owner = gl.message.sender_address
        self.balance = u256(0)

    @gl.public.write.payable
    def deposit(self) -> None:
        self.balance += gl.message.value

    @gl.public.write
    def withdraw(self, amount: u256) -> None:
        assert amount <= self.balance, "insufficient balance"
        self.balance -= amount
```
