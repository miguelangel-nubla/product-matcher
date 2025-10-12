import {
  Badge,
  Box,
  Button,
  Card,
  Code,
  Dialog,
  HStack,
  IconButton,
  Input,
  Table,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { FiCopy, FiEye, FiEyeOff, FiPlus, FiTrash2 } from "react-icons/fi"
import type { ApiError } from "@/client"
import { Field } from "@/components/ui/field"
import { InputGroup } from "@/components/ui/input-group"
import { Toaster, toaster } from "@/components/ui/toaster"
import {
  type AccessTokenCreate,
  type AccessTokenCreated,
  type AccessTokenPublic,
  createAccessToken,
  readAccessTokens,
  revokeAccessToken,
} from "@/services/accessTokens"
import { handleError } from "@/utils"

interface CreateTokenForm {
  name: string
  expires_at: string
}

function ApiKeys() {
  const queryClient = useQueryClient()
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [createdToken, setCreatedToken] = useState<string | null>(null)
  const [showToken, setShowToken] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreateTokenForm>({
    defaultValues: {
      name: "",
      expires_at: "",
    },
  })

  // Fetch access tokens
  const { data: tokensData, isLoading } = useQuery({
    queryKey: ["access-tokens"],
    queryFn: () => readAccessTokens(),
  })

  // Create token mutation
  const createTokenMutation = useMutation({
    mutationFn: (tokenData: AccessTokenCreate) =>
      createAccessToken({ requestBody: tokenData }),
    onSuccess: (data: AccessTokenCreated) => {
      setCreatedToken(data.token)
      setShowToken(false)
      queryClient.invalidateQueries({ queryKey: ["access-tokens"] })
      toaster.create({
        title: "Success",
        description: "API key created successfully",
        type: "success",
      })
      reset()
    },
    onError: (error: ApiError) => {
      handleError(error)
    },
  })

  // Revoke token mutation
  const revokeTokenMutation = useMutation({
    mutationFn: (tokenId: string) => revokeAccessToken({ tokenId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["access-tokens"] })
      toaster.create({
        title: "Success",
        description: "API key revoked successfully",
        type: "success",
      })
    },
    onError: (error: ApiError) => {
      handleError(error)
    },
  })

  const onSubmit = (data: CreateTokenForm) => {
    const dateValue = new Date(data.expires_at)
    const expiresAt = dateValue.toISOString()

    createTokenMutation.mutate({
      name: data.name,
      expires_at: expiresAt,
    })
  }

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      toaster.create({
        title: "Copied",
        description: "API key copied to clipboard",
        type: "success",
      })
    } catch {
      toaster.create({
        title: "Error",
        description: "Failed to copy to clipboard",
        type: "error",
      })
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  const getStatusColor = (token: AccessTokenPublic) => {
    if (!token.is_active) return "red"
    if (token.expires_at && new Date(token.expires_at) < new Date())
      return "orange"
    return "green"
  }

  const getStatusText = (token: AccessTokenPublic) => {
    if (!token.is_active) return "Inactive"
    if (token.expires_at && new Date(token.expires_at) < new Date())
      return "Expired"
    return "Active"
  }

  const sortedTokens = tokensData?.data.sort((a, b) => {
    // First sort by active status (active first)
    if (a.is_active !== b.is_active) {
      return a.is_active ? -1 : 1
    }

    // Then sort by expiration date (soonest to expire first)
    if (a.expires_at && b.expires_at) {
      return new Date(a.expires_at).getTime() - new Date(b.expires_at).getTime()
    }

    // Tokens without expiration come after those with expiration
    if (a.expires_at && !b.expires_at) return -1
    if (!a.expires_at && b.expires_at) return 1

    // Finally, sort by creation date (newest first)
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })

  return (
    <VStack align="stretch" gap={6}>
      <Toaster />

      <Box>
        <HStack justify="space-between" mb={4}>
          <Box>
            <Text fontSize="lg" fontWeight="semibold">
              API Keys
            </Text>
            <Text fontSize="sm" color="gray.600">
              Manage your API keys for programmatic access
            </Text>
          </Box>
          <Button onClick={() => setIsCreateDialogOpen(true)} variant="solid">
            <FiPlus />
            Create API Key
          </Button>
        </HStack>

        {isLoading ? (
          <Text>Loading...</Text>
        ) : (
          <Card.Root>
            <Table.Root>
              <Table.Header>
                <Table.Row>
                  <Table.ColumnHeader>Name</Table.ColumnHeader>
                  <Table.ColumnHeader>Prefix</Table.ColumnHeader>
                  <Table.ColumnHeader>Status</Table.ColumnHeader>
                  <Table.ColumnHeader>Expires</Table.ColumnHeader>
                  <Table.ColumnHeader>Created</Table.ColumnHeader>
                  <Table.ColumnHeader>Last Used</Table.ColumnHeader>
                  <Table.ColumnHeader>Actions</Table.ColumnHeader>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {sortedTokens?.map((token) => (
                  <Table.Row key={token.id}>
                    <Table.Cell>
                      <Text fontWeight="medium">{token.name}</Text>
                    </Table.Cell>
                    <Table.Cell>
                      <Code>{token.prefix}...</Code>
                    </Table.Cell>
                    <Table.Cell>
                      <Badge colorPalette={getStatusColor(token)} size="sm">
                        {getStatusText(token)}
                      </Badge>
                    </Table.Cell>
                    <Table.Cell>
                      <Text fontSize="sm">{formatDate(token.expires_at)}</Text>
                    </Table.Cell>
                    <Table.Cell>
                      <Text fontSize="sm">{formatDate(token.created_at)}</Text>
                    </Table.Cell>
                    <Table.Cell>
                      <Text fontSize="sm">
                        {token.last_used_at
                          ? formatDate(token.last_used_at)
                          : "Never"}
                      </Text>
                    </Table.Cell>
                    <Table.Cell>
                      {token.is_active ? (
                        <IconButton
                          size="sm"
                          variant="ghost"
                          colorPalette="red"
                          onClick={() => revokeTokenMutation.mutate(token.id)}
                          loading={
                            revokeTokenMutation.isPending &&
                            revokeTokenMutation.variables === token.id
                          }
                          disabled={
                            revokeTokenMutation.isPending &&
                            revokeTokenMutation.variables === token.id
                          }
                        >
                          <FiTrash2 />
                        </IconButton>
                      ) : (
                        <Text fontSize="sm" color="gray.500">
                          Revoked
                        </Text>
                      )}
                    </Table.Cell>
                  </Table.Row>
                ))}
              </Table.Body>
            </Table.Root>
            {(!sortedTokens || sortedTokens.length === 0) && (
              <Box p={6} textAlign="center">
                <Text color="gray.600">No API keys found</Text>
              </Box>
            )}
          </Card.Root>
        )}
      </Box>

      {/* Create Token Dialog */}
      <Dialog.Root
        open={isCreateDialogOpen}
        onOpenChange={(e) => setIsCreateDialogOpen(e.open)}
      >
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content>
            <Dialog.Header>
              <Dialog.Title>Create New API Key</Dialog.Title>
            </Dialog.Header>
            <Dialog.Body>
              <VStack gap={4} as="form" onSubmit={handleSubmit(onSubmit)}>
                <Field
                  label="Name"
                  required
                  invalid={!!errors.name}
                  errorText={errors.name?.message}
                >
                  <Input
                    {...register("name", { required: "Name is required" })}
                    placeholder="My API Key"
                  />
                </Field>

                <Field
                  label="Expires At"
                  required
                  invalid={!!errors.expires_at}
                  errorText={errors.expires_at?.message}
                >
                  <Input
                    type="datetime-local"
                    {...register("expires_at", {
                      required: "Expiration date is required",
                    })}
                  />
                </Field>
              </VStack>
            </Dialog.Body>
            <Dialog.Footer>
              <Dialog.ActionTrigger asChild>
                <Button variant="outline">Cancel</Button>
              </Dialog.ActionTrigger>
              <Button onClick={handleSubmit(onSubmit)} loading={isSubmitting}>
                Create
              </Button>
            </Dialog.Footer>
          </Dialog.Content>
        </Dialog.Positioner>
      </Dialog.Root>

      {/* Token Display Dialog */}
      <Dialog.Root
        open={!!createdToken}
        onOpenChange={() => {
          setCreatedToken(null)
          setShowToken(false)
          setIsCreateDialogOpen(false)
        }}
      >
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content maxW="2xl" w="full">
            <Dialog.Header>
              <Dialog.Title>API Key Created Successfully</Dialog.Title>
            </Dialog.Header>
            <Dialog.Body p={6}>
              <VStack gap={6} align="stretch">
                <Box
                  p={4}
                  bg="orange.50"
                  borderRadius="md"
                  border="1px solid"
                  borderColor="orange.200"
                >
                  <HStack gap={2}>
                    <Text fontSize="lg">⚠️</Text>
                    <VStack align="start" gap={1}>
                      <Text fontWeight="semibold" color="orange.800">
                        Important: Save this token now
                      </Text>
                      <Text fontSize="sm" color="orange.700">
                        This is the only time you'll see the full token. Make
                        sure to copy and store it securely.
                      </Text>
                    </VStack>
                  </HStack>
                </Box>

                <Field label="Your API Key">
                  <VStack gap={3} align="stretch" w="full">
                    <InputGroup
                      w="full"
                      endElement={
                        <HStack gap={1}>
                          <IconButton
                            onClick={() => setShowToken(!showToken)}
                            variant="ghost"
                            size="sm"
                            title={showToken ? "Hide token" : "Show token"}
                          >
                            {showToken ? <FiEyeOff /> : <FiEye />}
                          </IconButton>
                          <IconButton
                            onClick={() => copyToClipboard(createdToken || "")}
                            variant="ghost"
                            size="sm"
                            title="Copy to clipboard"
                          >
                            <FiCopy />
                          </IconButton>
                        </HStack>
                      }
                    >
                      <Input
                        value={createdToken || ""}
                        type={showToken ? "text" : "password"}
                        readOnly
                        fontFamily="mono"
                        fontSize="sm"
                      />
                    </InputGroup>

                    <Text fontSize="xs" color="gray.600">
                      Include this token in the Authorization header:{" "}
                      <Code fontSize="xs">
                        Bearer {createdToken?.substring(0, 8)}...
                      </Code>
                    </Text>
                  </VStack>
                </Field>
              </VStack>
            </Dialog.Body>
            <Dialog.Footer gap={3}>
              <Button
                variant="outline"
                onClick={() => copyToClipboard(createdToken || "")}
              >
                Copy Token
              </Button>
              <Button
                onClick={() => {
                  setCreatedToken(null)
                  setShowToken(false)
                  setIsCreateDialogOpen(false)
                }}
              >
                Done
              </Button>
            </Dialog.Footer>
          </Dialog.Content>
        </Dialog.Positioner>
      </Dialog.Root>
    </VStack>
  )
}

export default ApiKeys
