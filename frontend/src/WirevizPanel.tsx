
// Import for type checking
import { checkPluginVersion, type InvenTreePluginContext } from '@inventreedb/ui';
import { apiUrl } from '@inventreedb/ui';
import { ActionIcon, Alert, Anchor, Button, Divider, Group, Image, Menu, Paper, SimpleGrid, Stack, Table, Text, Title } from '@mantine/core';
import { IconDotsVertical, IconTrash, IconUpload } from '@tabler/icons-react';
import { useMemo } from 'react';


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


function WirevizPanel({context}: {context: InvenTreePluginContext}) {

    const wirevizContext = useMemo(() => context?.context ?? {}, [context]);

    const bomRows = useMemo(() => wirevizContext.wireviz_bom_data ?? [], [wirevizContext]);

    const wirevizDiagram = useMemo(() => wirevizContext.wireviz_svg_file ?? null, [wirevizContext]);

    const wirevizErrors = useMemo(() => wirevizContext.wireviz_errors ?? [], [wirevizContext]);

    const wirevizWarnings = useMemo(() => wirevizContext.wireviz_warnings ?? [], [wirevizContext]);

    const wirevizSource = useMemo(() => wirevizContext.wireviz_source_file ?? null, [wirevizContext]);

    const newDiagram = context.forms.create({
        title: 'Upload New Wireviz Diagram',
        url: apiUrl("/plugin/wireviz/upload/"),
        method: 'POST',
        fields: {
            part: {
                value: context.id,
                hidden: true,
            },
            file: {},
        }
    });

    return (
        <>
        {newDiagram.modal}
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
                <Alert color="red" title={"No Diagram Available"}>
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
        <Button onClick={newDiagram.open} color="blue">Upload New Wireviz Diagram</Button>
        </Stack>
        </>
    );
}


// Render the Wireviz panel against the provided target element
export function renderWirevizPanel(context: InvenTreePluginContext) {
    checkPluginVersion(context);
    return <WirevizPanel context={context} />;
}