export interface PersonnelEvent {
  type: string;
  name: string;
  personal_number: string | null;
  designation: string | null;
  event_date: string;
  age: number | null;
  years: number | null;
  event_label: string;
}

export interface PersonnelEventsResponse {
  status: string;
  count: number;
  from_date: string;
  to_date: string;
  today: PersonnelEvent[];
  tomorrow: PersonnelEvent[];
  upcoming: PersonnelEvent[];
  results: PersonnelEvent[];
}

export interface UserByIdResponse {
  id: number;
  username: string;
  profile?: {
    firstname?: string;
    lastname?: string;
    personal_number?: string | null;
    marriage_date?: string | null;
  };
}

export interface AnniversaryModalPayload {
  selectType: 'personal' | 'other';
  personnelId: string | null;
  name: string;
  personalNo: string;
  dateOfMarriage: string;
}

export interface PersonnelOption {
  id: string;
  name: string;
  personalNo: string;
}

export interface StoredUserData {
  id?: number;
}

export interface CommandMessagePayload {
  message: string;
  validTillDate: string;
}

export interface UpcomingEventUpdatePayload {
  title: string;
  start_date: string;
  end_date: string | null;
  start_time: string;
  end_time: null;
  category: null;
  description: null;
  document: File | null;
}

export interface ShipRole {
  id: number;
  title: string;
  description: string;
  uploadedDate: string;
}

export interface CoMessage {
  id: number;
  message: string;
  valid_till_date: string;
  uploaded_date: string;
}

export interface UpcomingEvent {
  id: number;
  title: string;
  date: string;
  document: string;
}

export interface DailyOrder {
  id: number;
  date: string;
  description: string;
  officer_details: string;
  routine_details: string;
  pdf_path: string;
}

export interface OfficerSpotlight {
  name: string;
  rank: string;
  role: string;
  image: string;
}

export interface SaveDailyOrderPayload {
  filename: string;
  source: string;
  pdf_path: string;
  roster_name: string;
  from_date: string;
  to_date: string;
  description: string;
  date: string;
  officer_details: string;
  routine_details: string;
}

export interface Quote {
  id?: number;
  quoteText?: string;
  is_active?: boolean;
}
