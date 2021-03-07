use crate::ansible;
use serde_with::{DeserializeFromStr, SerializeDisplay};
use std::fmt;
use std::str::FromStr;

#[derive(Eq, PartialEq, Copy, Clone, Debug, DeserializeFromStr, SerializeDisplay)]
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
    type Err = ansible::Error;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "ansible" => Ok(Product::Ansible),
            "ansible-base" => Ok(Product::AnsibleBase),
            "ansible-core" => Ok(Product::AnsibleCore),
            _ => Err(ansible::Error::parse_error(format!("Unknown product: {}", s))),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[allow(non_snake_case)]
    fn test_Product_FromStr() {
        assert_eq!(Product::from_str("ansible"), Ok(Product::Ansible));
        assert_eq!(Product::from_str("ansible-base"), Ok(Product::AnsibleBase));
        assert_eq!(Product::from_str("ansible-core"), Ok(Product::AnsibleCore));
        assert_eq!(
            Product::from_str("ansible-foo").unwrap_err(),
            ansible::Error::parse_error("Unknown product: ansible-foo".to_string()));
    }

    #[test]
    #[allow(non_snake_case)]
    fn test_Product_Display() {
        assert_eq!(format!("{}", Product::Ansible), "ansible");
        assert_eq!(format!("{}", Product::AnsibleBase), "ansible-base");
        assert_eq!(format!("{}", Product::AnsibleCore), "ansible-core");
    }
}
