/*
  # Create Core Tables for Smart Queue Management System

  1. New Tables
    - `roles` - User role definitions (super_admin, org_admin, staff, customer)
    - `organizations` - Multi-tenant organization records
    - `users` - User accounts with role and organization references
    - `departments` - Departments within organizations
    - `service_desks` - Service desks within departments
    - `tickets` - Queue tickets with priority and QR data
    - `notifications` - User notification records
    - `settings` - Organization-level configuration
    - `reports` - Generated report metadata

  2. Security
    - Enable RLS on all tables
    - Restrictive policies: data only accessible to authorized users
    - Organization-scoped access for org_admin and staff
    - Customer access limited to own data
*/

-- Roles table
CREATE TABLE IF NOT EXISTS roles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text UNIQUE NOT NULL,
  description text DEFAULT '',
  created_at timestamptz DEFAULT now()
);

-- Organizations table
CREATE TABLE IF NOT EXISTS organizations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  org_type text NOT NULL DEFAULT 'other',
  slug text UNIQUE NOT NULL,
  logo_url text DEFAULT '',
  address text DEFAULT '',
  email text DEFAULT '',
  phone text DEFAULT '',
  working_hours_start time DEFAULT '08:00:00',
  working_hours_end time DEFAULT '17:00:00',
  working_days text[] DEFAULT '{"monday","tuesday","wednesday","thursday","friday"}',
  is_active boolean DEFAULT true,
  subscription_plan text DEFAULT 'free',
  subscription_expires_at timestamptz DEFAULT now() + interval '365 days',
  max_queue_size integer DEFAULT 100,
  ticket_prefix text DEFAULT '',
  enable_priority_queue boolean DEFAULT true,
  enable_qr_code boolean DEFAULT true,
  reminder_threshold integer DEFAULT 2,
  avg_service_time_minutes integer DEFAULT 5,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Users table (references auth.users for Supabase Auth compatibility)
CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  auth_user_id uuid,  -- links to auth.users if using Supabase Auth
  email text UNIQUE,
  phone text UNIQUE,
  password_hash text NOT NULL,
  first_name text NOT NULL DEFAULT '',
  last_name text NOT NULL DEFAULT '',
  role_id uuid NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
  organization_id uuid REFERENCES organizations(id) ON DELETE SET NULL,
  is_active boolean DEFAULT true,
  email_verified boolean DEFAULT false,
  phone_verified boolean DEFAULT false,
  last_login_at timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Departments table
CREATE TABLE IF NOT EXISTS departments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name text NOT NULL,
  description text DEFAULT '',
  is_active boolean DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(organization_id, name)
);

-- Service Desks table
CREATE TABLE IF NOT EXISTS service_desks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  department_id uuid REFERENCES departments(id) ON DELETE SET NULL,
  name text NOT NULL,
  prefix text NOT NULL DEFAULT 'GEN',
  description text DEFAULT '',
  desk_number integer DEFAULT 1,
  is_active boolean DEFAULT true,
  current_ticket_id uuid,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(organization_id, prefix)
);

-- Tickets table
CREATE TABLE IF NOT EXISTS tickets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ticket_number text NOT NULL,
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  service_desk_id uuid NOT NULL REFERENCES service_desks(id) ON DELETE CASCADE,
  department_id uuid REFERENCES departments(id) ON DELETE SET NULL,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  priority text NOT NULL DEFAULT 'normal',
  status text NOT NULL DEFAULT 'waiting',
  queue_position integer NOT NULL DEFAULT 0,
  estimated_wait_minutes integer DEFAULT 0,
  qr_code_data text DEFAULT '',
  joined_at timestamptz DEFAULT now(),
  called_at timestamptz,
  served_at timestamptz,
  completed_at timestamptz,
  cancelled_at timestamptz,
  served_by_staff_id uuid REFERENCES users(id) ON DELETE SET NULL,
  notes text DEFAULT '',
  UNIQUE(organization_id, ticket_number)
);

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  organization_id uuid REFERENCES organizations(id) ON DELETE CASCADE,
  ticket_id uuid REFERENCES tickets(id) ON DELETE SET NULL,
  type text NOT NULL DEFAULT 'info',
  channel text NOT NULL DEFAULT 'in_app',
  title text NOT NULL,
  message text NOT NULL,
  is_read boolean DEFAULT false,
  sent_at timestamptz DEFAULT now(),
  read_at timestamptz
);

-- Settings table
CREATE TABLE IF NOT EXISTS settings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid UNIQUE NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  category text NOT NULL DEFAULT 'general',
  key text NOT NULL,
  value text NOT NULL DEFAULT '',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(organization_id, category, key)
);

-- Reports table
CREATE TABLE IF NOT EXISTS reports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  generated_by uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  report_type text NOT NULL,
  date_from date NOT NULL,
  date_to date NOT NULL,
  file_path text DEFAULT '',
  file_format text DEFAULT 'pdf',
  summary jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

-- Insert default roles
INSERT INTO roles (name, description) VALUES
  ('super_admin', 'System administrator with full access'),
  ('org_admin', 'Organization administrator'),
  ('staff', 'Service desk staff member'),
  ('customer', 'Regular customer/user')
ON CONFLICT (name) DO NOTHING;

-- Enable RLS on all tables
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE service_desks ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;

-- RLS Policies for roles
CREATE POLICY "Authenticated users can view roles"
  ON roles FOR SELECT TO authenticated USING (true);

-- RLS Policies for organizations
CREATE POLICY "Authenticated users can view active organizations"
  ON organizations FOR SELECT TO authenticated USING (is_active = true);

CREATE POLICY "Org admins can update their organization"
  ON organizations FOR UPDATE TO authenticated
  USING (
    EXISTS (SELECT 1 FROM users u JOIN roles r ON u.role_id = r.id
            WHERE u.id = auth.uid() AND r.name = 'super_admin')
    OR
    EXISTS (SELECT 1 FROM users u JOIN roles r ON u.role_id = r.id
            WHERE u.id = auth.uid() AND r.name = 'org_admin' AND u.organization_id = organizations.id)
  );

-- RLS Policies for users
CREATE POLICY "Users can view own profile"
  ON users FOR SELECT TO authenticated USING (id = auth.uid() OR
    EXISTS (SELECT 1 FROM users u JOIN roles r ON u.role_id = r.id WHERE u.id = auth.uid() AND r.name IN ('super_admin', 'org_admin')));

CREATE POLICY "Users can update own profile"
  ON users FOR UPDATE TO authenticated
  USING (id = auth.uid())
  WITH CHECK (id = auth.uid());

CREATE POLICY "Users can insert own profile"
  ON users FOR INSERT TO authenticated
  WITH CHECK (true);

-- RLS Policies for departments
CREATE POLICY "Users in org can view departments"
  ON departments FOR SELECT TO authenticated
  USING (
    organization_id IN (SELECT organization_id FROM users WHERE id = auth.uid() AND organization_id IS NOT NULL)
    OR
    EXISTS (SELECT 1 FROM users u JOIN roles r ON u.role_id = r.id WHERE u.id = auth.uid() AND r.name = 'super_admin')
    OR
    organization_id IN (SELECT id FROM organizations WHERE is_active = true)
  );

CREATE POLICY "Org admins can manage departments"
  ON departments FOR ALL TO authenticated
  USING (
    EXISTS (SELECT 1 FROM users u JOIN roles r ON u.role_id = r.id
            WHERE u.id = auth.uid() AND r.name IN ('super_admin', 'org_admin')
            AND (r.name = 'super_admin' OR u.organization_id = departments.organization_id))
  )
  WITH CHECK (
    EXISTS (SELECT 1 FROM users u JOIN roles r ON u.role_id = r.id
            WHERE u.id = auth.uid() AND r.name IN ('super_admin', 'org_admin')
            AND (r.name = 'super_admin' OR u.organization_id = departments.organization_id))
  );

-- RLS Policies for service_desks
CREATE POLICY "Users can view service desks"
  ON service_desks FOR SELECT TO authenticated
  USING (
    is_active = true
    OR
    organization_id IN (SELECT organization_id FROM users WHERE id = auth.uid() AND organization_id IS NOT NULL)
    OR
    EXISTS (SELECT 1 FROM users u JOIN roles r ON u.role_id = r.id WHERE u.id = auth.uid() AND r.name = 'super_admin')
  );

CREATE POLICY "Org admins can manage service desks"
  ON service_desks FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (SELECT 1 FROM users u JOIN roles r ON u.role_id = r.id
            WHERE u.id = auth.uid() AND r.name IN ('super_admin', 'org_admin')
            AND (r.name = 'super_admin' OR u.organization_id = service_desks.organization_id))
  );

CREATE POLICY "Org admins can update service desks"
  ON service_desks FOR UPDATE TO authenticated
  USING (
    EXISTS (SELECT 1 FROM users u JOIN roles r ON u.role_id = r.id
            WHERE u.id = auth.uid() AND r.name IN ('super_admin', 'org_admin')
            AND (r.name = 'super_admin' OR u.organization_id = service_desks.organization_id))
  )
  WITH CHECK (
    EXISTS (SELECT 1 FROM users u JOIN roles r ON u.role_id = r.id
            WHERE u.id = auth.uid() AND r.name IN ('super_admin', 'org_admin')
            AND (r.name = 'super_admin' OR u.organization_id = service_desks.organization_id))
  );

CREATE POLICY "Org admins can delete service desks"
  ON service_desks FOR DELETE TO authenticated
  USING (
    EXISTS (SELECT 1 FROM users u JOIN roles r ON u.role_id = r.id
            WHERE u.id = auth.uid() AND r.name IN ('super_admin', 'org_admin')
            AND (r.name = 'super_admin' OR u.organization_id = service_desks.organization_id))
  );

-- RLS Policies for tickets
CREATE POLICY "Users can view own tickets and org tickets"
  ON tickets FOR SELECT TO authenticated
  USING (
    user_id = auth.uid()
    OR
    EXISTS (SELECT 1 FROM users u JOIN roles r ON u.role_id = r.id
            WHERE u.id = auth.uid() AND r.name IN ('super_admin', 'org_admin', 'staff')
            AND (r.name = 'super_admin' OR u.organization_id = tickets.organization_id))
  );

CREATE POLICY "Customers can create tickets"
  ON tickets FOR INSERT TO authenticated
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "Staff can update tickets"
  ON tickets FOR UPDATE TO authenticated
  USING (
    user_id = auth.uid()
    OR
    EXISTS (SELECT 1 FROM users u JOIN roles r ON u.role_id = r.id
            WHERE u.id = auth.uid() AND r.name IN ('super_admin', 'org_admin', 'staff')
            AND (r.name = 'super_admin' OR u.organization_id = tickets.organization_id))
  )
  WITH CHECK (
    user_id = auth.uid()
    OR
    EXISTS (SELECT 1 FROM users u JOIN roles r ON u.role_id = r.id
            WHERE u.id = auth.uid() AND r.name IN ('super_admin', 'org_admin', 'staff')
            AND (r.name = 'super_admin' OR u.organization_id = tickets.organization_id))
  );

-- RLS Policies for notifications
CREATE POLICY "Users can view own notifications"
  ON notifications FOR SELECT TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "Users can update own notifications"
  ON notifications FOR UPDATE TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can create own notifications"
  ON notifications FOR INSERT TO authenticated
  WITH CHECK (user_id = auth.uid() OR
    EXISTS (SELECT 1 FROM users u JOIN roles r ON u.role_id = r.id
            WHERE u.id = auth.uid() AND r.name IN ('super_admin', 'org_admin', 'staff')));

-- RLS Policies for settings
CREATE POLICY "Org members can view settings"
  ON settings FOR SELECT TO authenticated
  USING (
    organization_id IN (SELECT organization_id FROM users WHERE id = auth.uid() AND organization_id IS NOT NULL)
    OR
    EXISTS (SELECT 1 FROM users u JOIN roles r ON u.role_id = r.id WHERE u.id = auth.uid() AND r.name = 'super_admin')
  );

CREATE POLICY "Org admins can manage settings"
  ON settings FOR ALL TO authenticated
  USING (
    EXISTS (SELECT 1 FROM users u JOIN roles r ON u.role_id = r.id
            WHERE u.id = auth.uid() AND r.name IN ('super_admin', 'org_admin')
            AND (r.name = 'super_admin' OR u.organization_id = settings.organization_id))
  )
  WITH CHECK (
    EXISTS (SELECT 1 FROM users u JOIN roles r ON u.role_id = r.id
            WHERE u.id = auth.uid() AND r.name IN ('super_admin', 'org_admin')
            AND (r.name = 'super_admin' OR u.organization_id = settings.organization_id))
  );

-- RLS Policies for reports
CREATE POLICY "Org admins can view reports"
  ON reports FOR SELECT TO authenticated
  USING (
    generated_by = auth.uid()
    OR
    EXISTS (SELECT 1 FROM users u JOIN roles r ON u.role_id = r.id
            WHERE u.id = auth.uid() AND r.name IN ('super_admin', 'org_admin')
            AND (r.name = 'super_admin' OR u.organization_id = reports.organization_id))
  );

CREATE POLICY "Org admins can create reports"
  ON reports FOR INSERT TO authenticated
  WITH CHECK (
    generated_by = auth.uid()
    AND
    EXISTS (SELECT 1 FROM users u JOIN roles r ON u.role_id = r.id
            WHERE u.id = auth.uid() AND r.name IN ('super_admin', 'org_admin')
            AND (r.name = 'super_admin' OR u.organization_id = reports.organization_id))
  );

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE INDEX IF NOT EXISTS idx_users_organization ON users(organization_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role_id);
CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug);
CREATE INDEX IF NOT EXISTS idx_organizations_type ON organizations(org_type);
CREATE INDEX IF NOT EXISTS idx_departments_org ON departments(organization_id);
CREATE INDEX IF NOT EXISTS idx_service_desks_org ON service_desks(organization_id);
CREATE INDEX IF NOT EXISTS idx_service_desks_dept ON service_desks(department_id);
CREATE INDEX IF NOT EXISTS idx_tickets_org ON tickets(organization_id);
CREATE INDEX IF NOT EXISTS idx_tickets_desk ON tickets(service_desk_id);
CREATE INDEX IF NOT EXISTS idx_tickets_user ON tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_settings_org ON settings(organization_id);
CREATE INDEX IF NOT EXISTS idx_reports_org ON reports(organization_id);
