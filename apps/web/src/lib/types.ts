export type Lens = "for_you" | "companies" | "skills" | "newsletters";
export type Tier = "critical" | "relevant" | "explore";
export type ProfileStatus = "targeting" | "placed";
export type CapabilityKind = "skill" | "tool";

export interface NamedRef { id: string; name: string }
/** A reader can follow at most this many fields of work. The API enforces the same limit. */
export const MAX_FIELDS = 4;

export interface RoleRef { id: string; title: string; domain?: NamedRef | null; parent?: NamedRef | null; mba?: boolean }
export interface CapabilityRef { id: string; name: string; kind: CapabilityKind; domain?: NamedRef | null; mba?: boolean }
export interface CompanyOut { id: string; name: string; industry: NamedRef | null; mba?: boolean }
export interface Domain {
  id: string;
  name: string;
  slug: string;
  group: string;
  role_count: number;
  family_count: number;
}

export interface Brief { paragraphs: string[]; pointers: string[]; note: string | null }

export interface Profile {
  user_id: string;
  name: string | null;
  profile_status: ProfileStatus;
  current_role: RoleRef | null;
  current_company: NamedRef | null;
  current_industry: NamedRef | null;
  placed_at: string | null;
  current_role_started_at: string | null;
  domains: NamedRef[];
  target_roles: RoleRef[];
  target_companies: NamedRef[];
  capabilities: CapabilityRef[];
}

export interface FeedItem {
  id: string;
  title: string;
  url: string;
  summary: string;
  brief: Brief | null;
  source: { name: string; authority: number };
  also_covered_by: string[];
  published_at: string;
  score: number;
  tier: Tier;
  why_this_matters: string;
  action: string;
  matched: { companies: string[]; roles: string[]; industries: string[]; capabilities: string[]; topics: string[] };
  domains: string[];
  saved: boolean;
  newsletter?: boolean;
}

export interface Feed {
  lens: Lens;
  summary: { total: number; critical: number; relevant: number; explore: number };
  items: FeedItem[];
  offset: number;
  has_more: boolean;
  as_of: string;
}

export interface SavedItem {
  id: string;
  title: string;
  url: string;
  summary: string;
  source: { name: string; authority: number };
  published_at: string;
  saved_at: string;
}

export interface CapabilityGap {
  capability_id: string;
  name: string;
  kind: CapabilityKind;
  required_by_count: number;
  required_by_total: number;
  gap_ratio: number;
  user_has_it: boolean;
  source: "jd" | "company" | "taxonomy";
}

export interface RoleGaps {
  role_id: string;
  role_title: string;
  companies_considered: number;
  companies_with_no_data: number;
  capabilities: CapabilityGap[];
}

export interface SkillGaps { user_id: string; target_roles: RoleGaps[] }

export interface ArticleBrief {
  id: string;
  title: string;
  url: string;
  summary: string;
  source: { name: string; authority: number };
  published_at: string;
  tags: { companies: string[]; capabilities: string[]; topics: string[] };
}

export interface RelatedRole { role: RoleRef; shared_capabilities: string[]; similarity: number }

export interface RoleDetail {
  id: string;
  title: string;
  domain: NamedRef | null;
  description: string | null;
  canonical: NamedRef | null;
  aliases: string[];
  variants: string[];
  capabilities: CapabilityRef[];
  companies: CompanyOut[];
  companies_total: number;
  related_roles: RelatedRole[];
}

export interface CompanyDetail {
  id: string;
  name: string;
  industry: NamedRef | null;
  website: string | null;
  roles_by_domain: { domain: NamedRef | null; roles: RoleRef[]; total: number }[];
  articles: ArticleBrief[];
}

export interface WebResult { title: string; snippet: string; url: string }

export interface RoleSuggestResult { matches: RoleRef[]; web_results: WebResult[] }
export interface CompanySuggestResult { matches: CompanyOut[]; web_results: WebResult[]; site_meta: WebResult | null }

export interface AddRoleBody { title: string; domain_id?: string | null; description?: string | null }
export interface AddCompanyBody { name: string; website?: string | null }

export interface SearchResults {
  query: string;
  roles: RoleRef[];
  companies: CompanyOut[];
  capabilities: CapabilityRef[];
  articles: ArticleBrief[];
}

export interface TargetsBody {
  domain_ids: string[];
  target_role_ids: string[];
  target_company_ids: string[];
  capability_ids: string[];
}

export interface ConsentBody { terms_version: string; privacy_version: string; over_18: boolean }

export interface LegalInfo {
  terms_version: string;
  privacy_version: string;
  operator_name: string | null;
  contact_email: string | null;
  grievance_officer: string | null;
  grievance_email: string | null;
  postal_address: string | null;
  hosting_region: string | null;
}

export interface OnboardingBody extends TargetsBody {
  name?: string | null;
  consent?: ConsentBody | null;
  current?: { company_id: string; role_id: string; industry_id?: string | null } | null;
}

export interface PlacementBody {
  company_id: string;
  role_id: string;
  industry_id?: string | null;
  placed_on?: string | null;
  clear_targets?: boolean;
}

export interface PlacementResult {
  event_type: "placed" | "role_changed" | "unchanged";
  profile_status: ProfileStatus;
}

export interface JDSkill { capability_id: string; name: string; kind: CapabilityKind; user_has_it: boolean }

export interface JD {
  id: string;
  title: string | null;
  company: NamedRef | null;
  role: RoleRef | null;
  company_name: string | null;
  created_at: string;
  skills: JDSkill[];
  coverage: number;
}

export interface JDBody {
  text: string;
  title?: string | null;
  company_id?: string | null;
  role_id?: string | null;
  company_name?: string | null;
}

export interface JDGap {
  capability_id: string;
  name: string;
  kind: CapabilityKind;
  jd_count: number;
  jd_total: number;
  user_has_it: boolean;
}

export interface JDGaps { jd_count: number; coverage: number; skills: JDGap[] }

export interface AuthResult { user_id: string; email: string; onboarded: boolean }

export interface Headline { title: string; url: string; source: string; field: string | null; published_at: string }

export interface Pulse {
  job_titles: number;
  companies: number;
  skills_and_tools: number;
  fields: number;
  stories_today: number;
  stories_total: number;
  sources: number;
  updated_at: string | null;
  headlines: Headline[];
}

export interface Streak {
  current_streak: number;
  longest_streak: number;
  active_today: boolean;
}

export type BadgeKind = "streak" | "articles" | "time";

export interface Badge {
  id: string;
  kind: BadgeKind;
  label: string;
  description: string;
  threshold: number;
  current: number;
  achieved: boolean;
}

export interface Badges { badges: Badge[] }

export type PushCategoryId = "streak" | "news" | "games" | "role_update" | "company_update";
export type PushCategories = Record<string, string>; // category id -> display label

export interface PushKeys {
  p256dh: string;
  auth: string;
}

export interface PushSubscribeBody {
  endpoint: string;
  keys: PushKeys;
  categories: string[];
}

export interface PushSubscriptionInfo {
  id: string;
  endpoint: string;
  categories: string[];
}
