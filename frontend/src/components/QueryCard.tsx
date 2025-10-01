import { Badge, Box, HStack, Text, VStack } from "@chakra-ui/react"

interface QueryCardProps {
  originalText: string
  normalizedText: string
  backend: string
  createdAt?: string
}

export function QueryCard({
  originalText,
  normalizedText,
  backend,
  createdAt,
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
          <Text
            fontWeight="semibold"
            fontSize="md"
            color="fg.emphasized"
            lineHeight="short"
          >
            "{originalText}"
          </Text>
          <Badge colorScheme="blue" size="sm" flexShrink={0}>
            {backend}
          </Badge>
        </HStack>

        <Text fontSize="sm" color="fg.muted">
          Normalized:{" "}
          <Text as="span" fontWeight="medium" color="fg.default">
            {normalizedText}
          </Text>
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
