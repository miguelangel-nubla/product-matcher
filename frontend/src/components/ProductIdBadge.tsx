import { Badge, Link } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { BackendsService } from "../client"

interface ProductIdBadgeProps {
  productId: string
  backend: string
  size?: "xs" | "sm" | "md" | "lg"
  colorScheme?: string
}

export function ProductIdBadge({
  productId,
  backend,
  size = "sm",
  colorScheme = "blue",
}: ProductIdBadgeProps) {
  // Fetch product URL
  const { data: productUrlData } = useQuery({
    queryKey: ["product-url", backend, productId],
    queryFn: () =>
      BackendsService.getProductUrl({ backend, productId }),
    enabled: !!(backend && productId),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  })

  // If we have a URL, make it clickable
  if ((productUrlData as any)?.url) {
    return (
      <Link
        href={(productUrlData as any).url}
        target="_blank"
        rel="noopener noreferrer"
        _hover={{ textDecoration: "none" }}
      >
        <Badge
          colorScheme={colorScheme}
          size={size}
          cursor="pointer"
          _hover={{ bg: `${colorScheme}.600` }}
        >
          {productId}
        </Badge>
      </Link>
    )
  }

  // Otherwise, just return the badge
  return (
    <Badge
      colorScheme={colorScheme}
      size={size}
      cursor="default"
    >
      {productId}
    </Badge>
  )
}