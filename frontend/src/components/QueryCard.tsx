import {
  Badge,
  Box,
  Button,
  Code,
  HStack,
  Text,
  VStack,
} from "@chakra-ui/react"

interface QueryCardProps {
  originalText: string
  normalizedText: string
  backend: string
  createdAt?: string
  onOriginalTextClick?: () => void
}

export function QueryCard({
  originalText,
  normalizedText,
  backend,
  createdAt,
  onOriginalTextClick,
}: QueryCardProps) {
  return (
    <Box
      p={4}
      borderRadius="lg"
      width="full"
      bg="bg.muted"
      border="1px solid"
      borderColor="border.muted"
    >
      <VStack gap={2} align="stretch" width="full">
        <HStack justify="space-between" align="start">
          {onOriginalTextClick ? (
            <Button
              variant="subtle"
              size="xs"
              px={2}
              py={1}
              onClick={onOriginalTextClick}
            >
              {originalText}
            </Button>
          ) : (
            <Text
              fontWeight="semibold"
              fontSize="md"
              color="fg.emphasized"
              lineHeight="short"
            >
              {originalText}
            </Text>
          )}
          <Badge variant="outline" size="sm" flexShrink={0}>
            {backend}
          </Badge>
        </HStack>

        <Text fontSize="sm" color="fg.muted">
          Normalized:{" "}
          <Code fontSize="sm" variant="surface">
            {normalizedText}
          </Code>
        </Text>

        {createdAt && (
          <HStack gap={8} wrap="wrap" justify="space-between" width="full">
            <HStack gap={1}>
              <Text fontSize="xs" color="fg.muted">
                Created:
              </Text>
              <Text fontSize="xs" color="fg.default">
                {new Date(createdAt).toLocaleDateString()}
              </Text>
            </HStack>
          </HStack>
        )}
      </VStack>
    </Box>
  )
}
