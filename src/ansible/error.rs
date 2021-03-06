use std::error::Error as StdError;
use std::fmt;

#[derive(Debug)]
pub enum Error {
    ParseError(String),
    NoVersionFound,
    ReqwestError(reqwest::Error),
}

impl Error {
    #[inline]
    pub fn parse_error(input: String) -> Error {
        Error::ParseError(input)
    }
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::ParseError(input) => write!(f, "Failed to parse: {}", input),
            Error::NoVersionFound => write!(f, "No such version(s) found"),
            Error::ReqwestError(err) => write!(f, "HTTP (Reqwest) error: {}", err),
        }
    }
}

impl StdError for Error {}

impl From<reqwest::Error> for Error {
    #[inline]
    fn from(err: reqwest::Error) -> Error {
        Error::ReqwestError(err)
    }
}
