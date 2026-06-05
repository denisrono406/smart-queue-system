/*
  # Fix RLS Policy on Users Table - Remove Unrestricted INSERT

  1. Security Fix
    - Drop the overly permissive "Users can insert own profile" INSERT policy
      that used `WITH CHECK (true)`, allowing any authenticated user to insert
      any row into the users table.
    - Replace it with a restrictive policy that only allows inserting a row
      where the new user's `id` matches `auth.uid()`, so users can only create
      their own profile record.

  2. Why this matters
    - `WITH CHECK (true)` means any authenticated user could INSERT arbitrary
      rows with any id, role_id, or organization_id — effectively bypassing
      all row-level security.
    - The replacement policy ensures a user can only insert a row where their
      own auth identity matches the row being created.
*/

-- Drop the overly permissive INSERT policy
DROP POLICY IF EXISTS "Users can insert own profile" ON users;

-- Replace with a properly restrictive INSERT policy
CREATE POLICY "Users can insert own profile"
  ON users FOR INSERT
  TO authenticated
  WITH CHECK (id = auth.uid());