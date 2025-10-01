import {
  Badge,
  Box,
  HStack,
  Link,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { BackendsService, MatchingService } from "../client"

interface ExternalProduct {
  id: string
  aliases: string[]
  description?: string
  category?: string
  barcode?: string
}

interface ProductCardProps {
  // Auto-fetch mode: provide ID and backend
  id?: string
  backend?: string

  // Manual mode: provide full product data
  product?: ExternalProduct

  // Common props
  confidence?: number
  isSelected?: boolean
  onClick?: () => void
}

export function ProductCard({
  id,
  backend,
  product,
  confidence,
  isSelected,
  onClick,
}: ProductCardProps) {
  // Auto-fetch product data if ID and backend provided
  const { data: fetchedProducts, isLoading } = useQuery({
    queryKey: ["external-products", backend],
    queryFn: () => MatchingService.getExternalProducts({ backend: backend! }),
    enabled: !!(id && backend && !product),
  })

  // Fetch product URL if ID and backend provided
  const { data: productUrlData } = useQuery({
    queryKey: ["product-url", backend, id],
    queryFn: () =>
      BackendsService.getProductUrl({ backend: backend!, productId: id! }),
    enabled: !!(id && backend),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  })

  // Find the specific product from fetched data
  const productData =
    product ||
    (fetchedProducts as any)?.data?.find((p: ExternalProduct) => p.id === id)

  if (!product && isLoading) {
    return (
      <Box p={4} borderWidth="1px" borderRadius="md" bg="bg.subtle">
        <HStack justify="center">
          <Spinner size="sm" />
          <Text fontSize="sm">Loading product...</Text>
        </HStack>
      </Box>
    )
  }

  if (!productData) {
    return (
      <Box p={4} borderWidth="1px" borderRadius="md" bg="bg.subtle">
        <Text fontSize="sm" color="fg.muted">
          Product not found
        </Text>
      </Box>
    )
  }
  return (
    <Box
      bg={isSelected ? "blue.subtle" : "bg.muted"}
      p={4}
      borderRadius="lg"
      border="1px solid"
      borderColor={isSelected ? "blue.solid" : "border.muted"}
      cursor={onClick ? "pointer" : "default"}
      onClick={onClick}
      _hover={onClick ? { borderColor: "blue.solid", bg: "blue.subtle" } : {}}
      width="full"
    >
      <VStack gap={2} align="stretch" width="full">
        <HStack justify="space-between" align="start">
          <Text
            fontWeight="semibold"
            fontSize="md"
            color="fg.emphasized"
            lineHeight="short"
          >
            {productData.aliases[0]}
          </Text>
          <HStack gap={2} flexShrink={0}>
            {confidence !== undefined && (
              <Badge
                size="sm"
                colorScheme={
                  confidence > 0.8
                    ? "green"
                    : confidence > 0.5
                      ? "yellow"
                      : "red"
                }
              >
                {(confidence * 100).toFixed(1)}%
              </Badge>
            )}
            {(productUrlData as any)?.url ? (
              <Link
                href={(productUrlData as any).url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Badge
                  colorScheme="blue"
                  size="sm"
                  cursor="pointer"
                  _hover={{ bg: "blue.700" }}
                >
                  {productData.id}
                </Badge>
              </Link>
            ) : (
              <Badge colorScheme="blue" size="sm">
                {productData.id}
              </Badge>
            )}
          </HStack>
        </HStack>

        {productData.aliases.length > 1 && (
          <Text fontSize="sm" color="fg.muted">
            Aliases:{" "}
            <Text as="span" fontWeight="medium" color="fg.default">
              {productData.aliases.slice(1).join(", ")}
            </Text>
          </Text>
        )}

        {productData.description && (
          <Text fontSize="sm" color="fg.muted">
            {productData.description}
          </Text>
        )}

        <HStack gap={4} wrap="wrap" width="full">
          {productData.category && (
            <HStack gap={1}>
              <Text fontSize="xs" color="fg.muted">
                Category:
              </Text>
              <Badge size="xs">{productData.category}</Badge>
            </HStack>
          )}

          {productData.barcode && (
            <HStack gap={1}>
              <Text fontSize="xs" color="fg.muted">
                Barcode:
              </Text>
              <Badge size="xs" variant="outline">
                {productData.barcode}
              </Badge>
            </HStack>
          )}
        </HStack>
      </VStack>
    </Box>
  )
}
