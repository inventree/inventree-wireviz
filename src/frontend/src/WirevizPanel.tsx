import '@mantine/core/styles.css';

import { IconDotsVertical, IconTrash, IconUpload } from '@tabler/icons-react';
import { ActionIcon, Alert, Anchor, Divider, Group, Image, MantineProvider, MantineTheme, Menu, Paper, SimpleGrid, Stack, Table, Text, Title } from "@mantine/core";
import { StrictMode, useMemo } from "react";
import { createRoot } from "react-dom/client";


function WirevizBomRow({row}: {row: any}) {

    const hasPartLink: boolean = !!row.sub_part && !!row.pn;

    return (
        <Table.Tr key={`bom-${row.idx}`}>
            <Table.Td key='col-idx'>{row.idx}</Table.Td>
            <Table.Td key='col-dsg'>{row.designators}</Table.Td>
            <Table.Td key='col-dsc'>{row.description}</Table.Td>
            <Table.Td key='col-qua'>
                <Group gap="xs" wrap="nowrap">
                    <Text key='quantity'>{row.quantity}</Text>
                    {row.unit && <Text key='unit' size="sm">{row.unit}</Text>}
                </Group>
            </Table.Td>
            <Table.Td key='col-prt'>
                {hasPartLink ? (
                    <Anchor href={`/part/${row.sub_part}/`}>{row.pn}</Anchor>
                ) : (
                    <Text>-</Text>
                )}
            </Table.Td>
        </Table.Tr>
    )

}


function WirevizPanel({context}: {context: any}) {

    const wirevizContext = useMemo(() => context?.context ?? {}, [context]);

    const bomRows = useMemo(() => wirevizContext.wireviz_bom_data ?? [], [wirevizContext]);

    const wirevizDiagram = useMemo(() => wirevizContext.wireviz_svg_file ?? null, [wirevizContext]);

    const wirevizErrors = useMemo(() => wirevizContext.wireviz_errors ?? [], [wirevizContext]);

    const wirevizWarnings = useMemo(() => wirevizContext.wireviz_warnings ?? [], [wirevizContext]);

    const wirevizSource = useMemo(() => wirevizContext.wireviz_source_file ?? null, [wirevizContext]);

    return (
        <>
        <Stack gap="xs" w="100%">
            {wirevizErrors && wirevizErrors.length > 0 && (
                <Alert color="red" title="Wireviz Errors">
                    <Stack gap="xs">
                        {wirevizErrors.map((error: string) => (
                            <Text key={error}>{error}</Text>
                        ))}
                    </Stack>
                </Alert>
            )}
            {wirevizWarnings && wirevizWarnings.length > 0 && (
                <Alert color="yellow" title="Wireviz Warnings">
                    <Stack gap="xs">
                        {wirevizWarnings.map((warning: string) => (
                            <Text key={warning}>{warning}</Text>
                        ))}
                    </Stack>
                </Alert>
            )}
        <SimpleGrid cols={2}>
            <Paper shadow="lg" p="md">
        <Stack gap="xs">
            <Group justify='space-between'>
            <Title order={4}>Harness Diagram</Title>
            <Menu position='left'>
                <Menu.Target>
                    <ActionIcon variant="transparent">
                        <IconDotsVertical />
                    </ActionIcon>
                </Menu.Target>
                <Menu.Dropdown>
                    <Menu.Item leftSection={<IconUpload />} >Upload New Diagram</Menu.Item>
                    <Menu.Item leftSection={<IconTrash color="red"/>}>Remove Diagram</Menu.Item>
                </Menu.Dropdown>
            </Menu>
            </Group>
            <Divider />
            {wirevizDiagram ? (
                <Image src={wirevizDiagram} alt="Wireviz diagram" />
            ) : (
                <Alert color="red" title={"No Diagram Avaialable"}>
                    <Text>No Wireviz diagram available for this part</Text>
                </Alert>
            )}
        </Stack>    
            </Paper>
        <Paper shadow="lg" p="md">
        <Stack gap="xs">
            <Title order={4}>Bill of Materials</Title>
            <Divider />
            <Table>
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th>ID</Table.Th>
                        <Table.Th>Designators</Table.Th>
                        <Table.Th>Description</Table.Th>
                        <Table.Th>Quantity</Table.Th>
                        <Table.Th>Part</Table.Th>
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                    {bomRows.map((row: any) => (
                        <WirevizBomRow row={row} />
                    ))}
                </Table.Tbody>
            </Table>
        </Stack>
        </Paper>
        </SimpleGrid>
        {wirevizSource && (
            <Paper shadow="lg" p="md">
                <Anchor href={wirevizSource} target="_blank">Wireviz Source File</Anchor>
            </Paper>
        )}
        </Stack>
        </>
    );
}


/**
 * Render the Wireviz panel against the provided target element
 * @param target 
 * @param context 
 */
export function renderPanel(target: HTMLElement | null, context: any) {

    createRoot(target!).render(
        <StrictMode>
            <MantineProvider theme={context.theme as MantineTheme}>
                <WirevizPanel context={context}/>
            </MantineProvider>
        </StrictMode>
    );
}