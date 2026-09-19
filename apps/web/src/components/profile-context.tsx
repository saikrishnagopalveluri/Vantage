"use client";

import { createContext, useContext } from "react";
import type { Profile } from "@/lib/types";

interface ProfileContextValue {
  profile: Profile;
  reload: () => void;
  setProfile: (profile: Profile) => void;
}

export const ProfileContext = createContext<ProfileContextValue | null>(null);

export function useProfile(): ProfileContextValue {
  const value = useContext(ProfileContext);
  if (!value) throw new Error("useProfile must be used inside the app shell");
  return value;
}
