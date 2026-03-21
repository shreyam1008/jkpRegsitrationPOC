import { useQuery } from "@tanstack/react-query";
import { searchDevotees } from "@/api/satsangisApi";

export function useDevoteeSearch(query: string) {
  return useQuery({
    queryKey: ["devotees", query],
    queryFn: () => searchDevotees(query),
    refetchOnWindowFocus: false,
  });
}
