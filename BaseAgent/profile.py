# profile.py
class AgentProfile:
    def __init__(self, company: str, code: str, market: str):
        self.company = company
        self.code = code
        self.market = market
        self.comfig = {
            'name': company,
            'code': code,
            'market': market
        }

    def get_identity(self) -> str:
        return f"{self.company}（{self.market}:{self.code}）"
    
    def get_config(self) -> dict:
        return self.comfig
