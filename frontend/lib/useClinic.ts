"use client";

import { useEffect, useState } from "react";
import { createClient } from "./supabase/client";

export type Clinic = {
  id: string;
  name: string;
  email: string | null;
  phone_number: string | null;
  subscription_status: string | null;
};

export function useClinic() {
  const [clinic, setClinic] = useState<Clinic | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const supabase = createClient();
    supabase
      .from("clinics")
      .select("id,name,email,phone_number,subscription_status")
      .limit(1)
      .single()
      .then(({ data, error }) => {
        if (error && error.code !== "PGRST116") {
          setError(error.message);
        } else {
          setClinic((data as Clinic) ?? null);
        }
        setLoading(false);
      });
  }, []);

  return { clinic, loading, error };
}
