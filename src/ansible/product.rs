use crate::ansible::error::*;
use std::fmt;
use std::str::FromStr;

#[derive(Eq, PartialEq, Copy, Clone, Debug)]
pub enum Product {
    Ansible,
    AnsibleBase,
    AnsibleCore,
}

impl fmt::Display for Product {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let product = match self {
            Product::Ansible => "ansible",
            Product::AnsibleBase => "ansible-base",
            Product::AnsibleCore => "ansible-core",
        };
        write!(f, "{}", product)
    }
}

impl FromStr for Product {
    type Err = AnsibleParseError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "ansible" => Ok(Product::Ansible),
            "ansible-base" => Ok(Product::AnsibleBase),
            "ansible-core" => Ok(Product::AnsibleCore),
            _ => Err(AnsibleParseError::new(format!("Unknown product: {}", s))),
        }
    }
}
