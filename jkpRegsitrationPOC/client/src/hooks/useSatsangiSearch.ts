import { useQuery } from "@tanstack/react-query";
import { searchSatsangis } from "@/api/satsangisApi";

export function useSatsangiSearch(query: string) {
  return useQuery({
    queryKey: ["satsangis", query],
    queryFn: () => searchSatsangis(query),
    refetchOnWindowFocus: false,
  });
}
