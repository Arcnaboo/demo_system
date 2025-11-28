import logging, random
import os

BASE = os.path.dirname(__file__)
WORDS = os.path.join(BASE, "words.txt")
DOMAINS = os.path.join(BASE, "domains.txt")



class Generator:
    def __init__(self):
        try:
            self._words = []
            self._domains = []
            with open(WORDS,"r") as _wfile:
                for line in _wfile:
                    self._words.append(line.strip())
            with open(DOMAINS) as _dfile:
                for line in _dfile:
                    self._domains.append(line.strip())
        except Exception as e:
            logging.info(f"[Generator] error:{e}")

    
    def get_int(self):
        i = int(random.random() * 100)
        return i
    
    def get_one_or_two(self):
        outs = [128, 256]
        return outs[(self.get_int() % 2)]
    
    def get_word(self):
        i = self.get_int()
        l = len(self._words)
        w = self._words[i % l]
        return w 
    
    def get_domain(self):
        i = self.get_int()
        l = len(self._domains)
        w = self._domains[i % l]
        return w 
    
    def get_email(self):
        mail = f"{self.get_word()}@{self.get_domain()}"
        return mail
    



generator = Generator()


        
