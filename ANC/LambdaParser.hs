{-# LANGUAGE DeriveGeneric #-}

module LambdaParser where

import Text.Parsec.Language (emptyDef)
import qualified Text.Parsec.Token as P
import Text.Parsec.Char
import Text.Parsec.Prim
import Text.Parsec.Combinator
import Text.Parsec.String (Parser)
import Text.Parsec.Error
import Control.Applicative (liftA2)
import Data.Aeson
import GHC.Generics
import ForLambdaCommon

data ProgLambda = UnitLambda | IfL Cmp ProgLambda ProgLambda | ExprL Expr
                | LetLambda String ProgLambda ProgLambda | LetRecLambda String String ProgLambda ProgLambda 
                | App App deriving Generic

data App = SimpleApp String Expr | ComplexApp App Expr deriving Generic

instance Show ProgLambda where
  show UnitLambda = "unit"
  show (IfL c p1 p2) = "if " ++ show c ++ " then " ++ show p1 ++ " else " ++ show p2
  show (ExprL e) = show e
  show (LetLambda s p1 p2) = "let " ++ s ++ " = " ++ show p1 ++ " in " ++ show p2
  show (LetRecLambda s1 s2 p1 p2) = "letrec " ++ s1 ++ " " ++ s2 ++ " = " ++ show p1 ++ " in " ++ show p2
  show (App a) = show a

instance Show App where
  show (SimpleApp s e) = s ++ " " ++ show e
  show (ComplexApp a e) = "(" ++ show a ++ ") " ++ show e 

instance ToJSON App where
    toEncoding = genericToEncoding defaultOptions

instance FromJSON App

instance ToJSON ProgLambda where
    toEncoding = genericToEncoding defaultOptions

instance FromJSON ProgLambda

progLambdaDef :: P.LanguageDef ()
progLambdaDef = emptyDef {P.identStart = letter,
                          P.identLetter = alphaNum,
                          P.opStart = P.opLetter progLambdaDef,
                          P.opLetter = oneOf "+-=;><",
                          P.reservedOpNames = [">", "<", "==", "=", "+", "-"],
                          P.reservedNames = ["if", "then", "else", "let", "in", "letrec", "unit"]}

lexer :: P.TokenParser ()
lexer = P.makeTokenParser progLambdaDef

reserved :: String -> Parser ()
reserved = P.reserved lexer

reservedOp :: String -> Parser ()
reservedOp = P.reserved lexer

double_equal :: Parser ()
double_equal = P.reservedOp lexer "=="

equal :: Parser ()
equal = P.reservedOp lexer "="

plus :: Parser ()
plus = P.reservedOp lexer "+"

minus :: Parser ()
minus = P.reservedOp lexer "-"

le :: Parser ()
le = P.reservedOp lexer "<"

ge :: Parser ()
ge = P.reservedOp lexer ">"

identifier :: Parser String
identifier = P.identifier lexer

parens :: Parser a -> Parser a
parens = P.parens lexer

exprL, exprL_term, varL, constL :: Parser Expr
exprL = exprL_term `chainl1` ((plus *> pure Plus) <|> (minus *> pure Minus))
exprL_term = varL <|> constL
varL = Var <$> identifier
constL = Const <$> P.integer lexer

cmpP :: Parser Cmp
cmpP = try (liftA2 Equal (exprL <* double_equal) exprL) <|>
       try (liftA2 Le (exprL <* le) exprL) <|>
       liftA2 (Ge) (exprL <* ge) exprL

progP, unitP, ifP, letP, letrecP :: Parser ProgLambda
progP = unitP <|> ifP <|> letP <|> letrecP <|> ExprL <$> exprL <|> parens progP

unitP = reserved "unit" *> pure UnitLambda

ifP = do
        reserved "if"
        cond <- cmpP
        reserved "then"
        if_body <- progP
        reserved "else"
        else_body <- progP
        return $ IfL cond if_body else_body

letP = do
        reserved "let"
        var <- identifier
        equal
        value <- progP
        reserved "in"
        body <- progP
        return $ LetLambda var value body


letrecP = do
            reserved "letrec"
            var1 <- identifier
            var2 <- identifier
            equal
            value <- progP
            reserved "in"
            body <- progP
            return $ LetRecLambda var1 var2 value body

parseProg :: String -> Either ParseError ProgLambda
parseProg = parse progP ""