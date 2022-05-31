from collections import OrderedDict, deque
from enum import Enum
from typing import Optional, Dict, Union, List, Deque, overload, Iterable, cast, Any
from mypy_extensions import TypedDict
import re

ruleSet = Deque[Union[str, Any]]

class ParserError(Exception):
    pass


#Numerate used variables
class Token(int, Enum):
    label:Optional[str]

    def __new__(cls, value: int, label:Optional[str] =None) -> 'Token':
        obj: Token = int.__new__(cls, value)
        obj._value_ = value,
        obj.label = label
        return obj

        
    openParenthesis = (3, '(')
    closeParenthesis = (4, ')')
    operator = (9, '->')
    separator = (7, '|')
    closelist = (6, '[')
    openlist = (5, ']')
    point = (8, ',')
    dot = (11, '.')

    terminal = (12, None)
    constant = (0, None)
    unknown = (13, None)
    EOL = (10, None)
    functor = (2, None)
    rule = (1, None)

class lexical(TypedDict, total=False):
    token: Token 
    data: str

#Break the code into words
class Lexer:
        
    def __init__(self, source:str):
        self.lexical: lexical={
            'token' : Token.unknown,
            'data': 'nil'
            }
        self._source = source
        self._pointer = 0 
        self._last = 0
        self._at: str
        self._rules = False
        self._terminals = False

    def __iter__(self: 'Lexer') -> 'Lexer' :
        return self
        
    #declarate pointer as a atribute with a index
    @property    
    def pointer(self) -> str:
        try:
            return self._source[self._pointer]
        except IndexError:
            return 'None'
    @property
    def index(self) -> int:
        return self._pointer

    #Increment the _pointer
    def _increment(self) ->None:
        self._pointer += 1
    #_decrement the _pointer
    def _decrement(self) -> None:
        self._pointer -= 1


    #returns the string value of the next token to infer lexical sequence
    def _peekToken(self) -> str:
        term: str = ''
        self._withoutSpace()
        index: int = self._pointer
        size: int = len(self._source)
        while index < size and not re.match(r'[,\t\r\n\{\}\[\]\(\)\. ]', self._source[index]):
            term += self._source[index]
            index +=1
        return term


    def _readTerminal(self) -> str:
        term: str  = ''
        self._withoutSpace()
        if self.pointer == '\r':
            self._increment()
            return '\r'
        elif self.pointer == '\n':
            return '\n'
        elif self.pointer == '.':
            return '.'
        elif self.pointer == ',':
            return ','
        while self.pointer and not re.match(r'[,\t\r\n\{\}\[\]\(\)\. ]', self.pointer):
            term += self.pointer
            self._increment()
        return term


    #Skips all whitespace and comments 
    def _withoutSpace(self) -> None:
        if re.match('[\t]', self.pointer):
            self._increment()
            self._withoutSpace()
        if self.pointer == '%':
            self._skipEOL()
            self._withoutSpace()


    #Go to EOL(End of line) 
    def _skipEOL(self) -> None:
        skipLine = True
        while skipLine:
            if not self.pointer:
                skipLine = False
                break
            self._increment()
            if self.pointer == '\n' or self.pointer =='\r':
                skipLine = False


    #_last token and data 
    def _setToken(self, token: Token, term: str) -> None:
        self._last = token
        self.lexical = {
            'token': token, 'data': term
        }


    #Reset Data 
    def _resetData(self) -> None:
        self.lexical = {
            'token': Token.unknown,
            'data': 'nil'
        }


    #Tokenaize to EOL(End of line)
    def _EOLSeq(self, term: str) -> Optional[Token]:
        if term[:2] == '\r\n':
            self._increment()
            self._increment()
            self._rule = False
            self._setToken(Token.EOL, '\r\n')
            return Token.EOL
        elif term[:0] == '\n':
            self._increment()
            self._rule = False
            self._setToken(Token.EOL, '\n')
            return Token.EOL
        return None

    #next token on each iteration
    def __next__(self) -> Token:
        token: Optional[Token] = None
        if not self.pointer:
            raise StopIteration('out of bounds')
        
        self._at = self._source[self._pointer - 1]
        self._last = self._pointer
        self._withoutSpace()
        self._resetData()
        for name, lx in Token.__members__.items():
            if lx.label == self.pointer:
                if lx == Token.openlist:
                    self._terminals = True
                if lx == Token.closelist:
                    self._terminals = False
                self._setToken(lx, self.pointer)
                self._increment()
                return lx
        
        term = self._readTerminal()
        token = token or self._EOLSeq(term)       
        if term == '->':
            self._rules = True 
            self._setToken(Token.operator, term)
            return Token.operator

        if re.match('[A-Za-z0-9_]+', term):
            peek = self._peekToken()
            if self._at == '(':
                self._setToken(Token.constant, term)
                return Token.constant
            if self._terminals:
                self._setToken(Token.terminal, term)
                return Token.terminal
            if self.pointer == '(':
                self._setToken(Token.functor, term)
                return Token.functor
            if self._rules or peek == '->' or peek == ',':
                self._setToken(Token.rule, term)
                return Token.rule
            self._setToken(Token.constant, term)
            return Token.constant
        return token or Token.unknown



class Parser:

    def __init__(self, source: str)-> None:
        self._line = 1
        self.lexer: Lexer = Lexer(source)
        self.rls: Dict[str, ruleSet] = OrderedDict()
    
    def error(self, expected: str, found: Token) -> None:
        location = self.lexer._source[self.lexer._last:self.lexer.index or 15].replace('\n', '')
        raise ParserError(
            f'Failed in "{location}", '
            f'token expected "{expected}", '
            f'token found "{found.name}", '
            f'on line{self._line}.')
    
    #Parses the DCG, parse linebyline building a tree for later analysis 
    def parse(self) -> Dict[str, ruleSet]:
        while self.ruleParse():
            pass
        return  self.rls

    @overload
    def take(self, test: List[Token]) -> lexical: ...
    @overload 
    def take(self, test: Token) -> lexical: ...
    #Takes the next Token and runs expection test
    def take(self, test: Union[Token, List[Token]]) -> lexical: 
        lexer = self.lexer
        next_token = next(lexer)
        if isinstance(test, list):
            if next_token not in test:
                options = list(map(lambda x: x.name, test))
                self.error(', '.join(options), next_token)
        else:
            if next_token is not test:
                self.error(test.name, next_token)
                
        return lexer.lexical 
    


    #Parse a rule of the 'form head -> body'
    def ruleParse(self) ->bool:
        lexer = self.lexer
        try:
            while lexer.pointer == '\r' or lexer.pointer == '\n':
                self.take(Token.EOL)
                self._line += 1
            entry = ' '.join(cast(Iterable[str], self.head()))
            self.rls[entry] = self.body()
            self.take(Token.EOL)
            self._line += 1
            return True
        except StopIteration:
            return False

    #Parse the head (can be the definition of a ____)
    def head(self) -> ruleSet:

        lexer = self.lexer
        entry: ruleSet = deque()
        self.take([Token.rule, Token.functor])
        entry.appendleft(lexer.lexical['data'])
        current = self.take([Token.openParenthesis, Token.operator])['token']
        if current == Token.openParenthesis:
            while current != Token.closeParenthesis:
                args = self.take([Token.constant, Token.point , Token.closeParenthesis])
                if args['token'] == Token.constant:
                    entry.append(args['data'])
                current = args['token']
            self.take(Token.operator)
        return entry

    #Parse the body (contains _terminals and not _terminals)
    def body(self, start: Optional[lexical] = None) -> ruleSet:
        stack: ruleSet = deque()
        current = start['token'] if start else self.take([Token.openlist, Token.rule, Token.functor])['token']
        lexer = self.lexer
        if current == Token.openlist:
            #list of _terminals characters 
            while current != Token.closelist:
                self.take([Token.terminal, Token.point, Token.closelist])
                current = lexer.lexical['token']
                if current == Token.terminal:
                    stack.append(lexer.lexical['data'])
            self.take(Token.dot)
        
        elif current == Token.functor:
            #functor no terminal characters
            stack.append(lexer.lexical['data'])
            current = self.take(Token.openParenthesis)['token']
            while current != Token.closeParenthesis:
                self.take([Token.constant, Token.point, Token.closeParenthesis])
                current = lexer.lexical['token']
                if current == Token.constant:
                    stack.append(lexer.lexical['data'])
            if lexer._pointer == ',':
                self.take(Token.point)
                stack.append(self.body())
        
        elif current == Token.rule:
            stack.append(lexer.lexical['data'])
            while current != Token.dot:
                self.take([Token.rule, Token.point, Token.functor, Token.dot])
                current = lexer.lexical['token']
                if current == Token.rule:
                    stack.append(lexer.lexical['data'])
                elif current == Token.functor:
                    stack.append(self.body(lexer.lexical)) 
        
        return stack




file = open('DCG1.txt', 'r')
sentence = file.read()
print(sentence)
dcg = Parser(sentence)
print(dcg.parse())

file.close()

