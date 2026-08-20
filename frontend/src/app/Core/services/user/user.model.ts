/**
 * Shape of the logged-in user returned by `api/v1/user/retrive/`. Only the
 * fields the app reads are declared explicitly; the index signature keeps the
 * type open for the many other server-provided fields without resorting to `any`.
 */
export interface UserProfile {
  image?: string;
  designation?: string;
  first_name?: string;
  last_name?: string;
  personnel_number?: string;
  rank?: string;
  nud_mail?: string;
  is_staff?: boolean;
  is_superuser?: boolean;
  roles?: string[];
  [key: string]: unknown;
}

export interface UserOption {
  id: number;
  full_name: string;
  personnel_number: string | null;
  rank: string | null;
}

export interface UserTicket {
  id?: number;
  title?: string;
  description?: string;
  status?: string;
  priority?: string;
  image?: string | null;
  assigned_members?: TeamMember[];
  created_at?: string;
  updated_at?: string;
  [key: string]: unknown;
}

export interface TeamMember {
  id?: number;
  name: string;
  rank?: string;
  landline?: string;
  mobile?: string;
  image?: string | null;
}
