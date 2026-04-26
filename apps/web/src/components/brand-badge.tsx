import { Badge } from "@/components/ui/badge";
import { brandColor, brandLabel } from "@/lib/filters";

export function BrandBadge({ brand }: { brand: string }) {
  return (
    <Badge variant="outline" className={brandColor(brand)}>
      {brandLabel(brand)}
    </Badge>
  );
}
