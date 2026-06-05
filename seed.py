"""Seed the database with initial data."""
from app import create_app
from app.extensions import db
from app.models import Role, User, Organization, Department, ServiceDesk, Setting
from app.utils import hash_password


def seed():
    app = create_app('development')
    with app.app_context():
        db.create_all()
        Role.insert_roles()

        # Create super admin
        super_admin_role = Role.query.filter_by(name='super_admin').first()
        org_admin_role = Role.query.filter_by(name='org_admin').first()
        staff_role = Role.query.filter_by(name='staff').first()
        customer_role = Role.query.filter_by(name='customer').first()

        if not User.query.filter_by(email='admin@queueapp.com').first():
            super_admin = User(
                first_name='System',
                last_name='Admin',
                email='admin@queueapp.com',
                password_hash=hash_password('Admin@123'),
                role_id=super_admin_role.id,
                is_active=True,
                email_verified=True,
            )
            db.session.add(super_admin)

        # Create sample organizations
        orgs_data = [
            {
                'name': 'City General Hospital',
                'org_type': 'hospital',
                'slug': 'city-general-hospital',
                'email': 'info@citygeneral.com',
                'phone': '+1234567890',
                'address': '123 Health Street, Medical District',
                'desks': [
                    {'name': 'Reception Desk', 'prefix': 'REC', 'department': 'General'},
                    {'name': 'Consultation Desk', 'prefix': 'CON', 'department': 'Outpatient'},
                    {'name': 'Pharmacy Desk', 'prefix': 'PHA', 'department': 'Pharmacy'},
                    {'name': 'Laboratory Desk', 'prefix': 'LAB', 'department': 'Laboratory'},
                ],
            },
            {
                'name': 'National Bank',
                'org_type': 'bank',
                'slug': 'national-bank',
                'email': 'info@nationalbank.com',
                'phone': '+1234567891',
                'address': '456 Finance Avenue, Business District',
                'desks': [
                    {'name': 'Customer Service', 'prefix': 'CS', 'department': 'Customer Relations'},
                    {'name': 'Loans Desk', 'prefix': 'LOA', 'department': 'Loans'},
                    {'name': 'Teller Desk', 'prefix': 'TEL', 'department': 'Banking Hall'},
                    {'name': 'Account Opening', 'prefix': 'ACC', 'department': 'Accounts'},
                ],
            },
            {
                'name': 'Sunrise University',
                'org_type': 'university',
                'slug': 'sunrise-university',
                'email': 'info@sunriseuni.edu',
                'phone': '+1234567892',
                'address': '789 Academic Boulevard, Education Zone',
                'desks': [
                    {'name': 'Admissions Desk', 'prefix': 'ADM', 'department': 'Admissions'},
                    {'name': 'Finance Desk', 'prefix': 'FIN', 'department': 'Finance'},
                    {'name': 'Examination Desk', 'prefix': 'EXA', 'department': 'Examinations'},
                    {'name': 'Registry Desk', 'prefix': 'REG', 'department': 'Registry'},
                ],
            },
        ]

        for org_data in orgs_data:
            org = Organization.query.filter_by(slug=org_data['slug']).first()
            if not org:
                org = Organization(
                    name=org_data['name'],
                    org_type=org_data['org_type'],
                    slug=org_data['slug'],
                    email=org_data['email'],
                    phone=org_data['phone'],
                    address=org_data['address'],
                )
                db.session.add(org)
                db.session.flush()

                # Create departments and desks
                for desk_data in org_data['desks']:
                    dept = Department(
                        organization_id=org.id,
                        name=desk_data['department'],
                    )
                    db.session.add(dept)
                    db.session.flush()

                    desk = ServiceDesk(
                        organization_id=org.id,
                        department_id=dept.id,
                        name=desk_data['name'],
                        prefix=desk_data['prefix'],
                        desk_number=1,
                    )
                    db.session.add(desk)

                # Create org admin
                org_admin = User(
                    first_name='Admin',
                    last_name=org.name.split()[0],
                    email=f'admin@{org.slug}.com',
                    password_hash=hash_password('Admin@123'),
                    role_id=org_admin_role.id,
                    organization_id=org.id,
                    is_active=True,
                    email_verified=True,
                )
                db.session.add(org_admin)

                # Create a staff member for first desk
                first_desk = org_data['desks'][0]
                staff_user = User(
                    first_name='Staff',
                    last_name=first_desk['prefix'],
                    email=f'staff.{first_desk["prefix"].lower()}@{org.slug}.com',
                    password_hash=hash_password('Staff@123'),
                    role_id=staff_role.id,
                    organization_id=org.id,
                    is_active=True,
                    email_verified=True,
                )
                db.session.add(staff_user)

                # Initialize settings
                for cat, key, val in [
                    ('auth', 'password_min_length', '8'),
                    ('auth', 'password_require_uppercase', 'true'),
                    ('auth', 'password_require_lowercase', 'true'),
                    ('auth', 'password_require_number', 'true'),
                    ('auth', 'password_require_special', 'true'),
                    ('notification', 'email_enabled', 'true'),
                    ('notification', 'sms_enabled', 'false'),
                    ('queue', 'max_queue_size', '100'),
                    ('queue', 'avg_service_time_minutes', '5'),
                    ('queue', 'reminder_threshold', '2'),
                    ('ticket', 'enable_qr_code', 'true'),
                    ('ticket', 'ticket_prefix', ''),
                    ('ticket', 'enable_priority_queue', 'true'),
                ]:
                    Setting.set_setting(org.id, cat, key, val)

        # Create a sample customer
        if not User.query.filter_by(email='customer@example.com').first():
            customer = User(
                first_name='John',
                last_name='Doe',
                email='customer@example.com',
                password_hash=hash_password('Customer@123'),
                role_id=customer_role.id,
                is_active=True,
                email_verified=True,
            )
            db.session.add(customer)

        db.session.commit()
        print('Database seeded successfully!')
        print('\nDefault accounts:')
        print('  Super Admin:  admin@queueapp.com / Admin@123')
        print('  Org Admin:    admin@city-general-hospital.com / Admin@123')
        print('  Org Admin:    admin@national-bank.com / Admin@123')
        print('  Org Admin:    admin@sunrise-university.com / Admin@123')
        print('  Staff:        staff.rec@city-general-hospital.com / Staff@123')
        print('  Customer:     customer@example.com / Customer@123')


if __name__ == '__main__':
    seed()
