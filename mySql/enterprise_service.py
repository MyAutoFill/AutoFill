"""Service layer for EnterpriseData operations."""

from mySql.enterprise_dbo import EnterpriseData
from mySql.database import db


def create_enterprise_data(data):
    """Create a new EnterpriseData record."""
    new_data = EnterpriseData(**data)
    db.session.add(new_data)
    db.session.commit()
    return new_data


def get_enterprise_data(data_id):
    """Retrieve an EnterpriseData record by ID."""
    return EnterpriseData.query.get(data_id)


def update_enterprise_data(data_id, updates):
    """Update an existing EnterpriseData record."""
    data = EnterpriseData.query.get(data_id)
    for key, value in updates.items():
        setattr(data, key, value)
    db.session.commit()
    return data


def delete_enterprise_data(data_id):
    """Delete an EnterpriseData record by ID."""
    data = EnterpriseData.query.get(data_id)
    db.session.delete(data)
    db.session.commit()
