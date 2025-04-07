
// Import for type checking
import { checkPluginVersion, type InvenTreePluginContext } from '@inventreedb/ui';
import { apiUrl, getDetailUrl, navigateToLink, ModelType } from '@inventreedb/ui';
import { ActionIcon, Alert, Anchor, Divider, Group, Image, Menu, Paper, SimpleGrid, Stack, Table, Text, Title } from '@mantine/core';
import { IconDotsVertical, IconFile, IconTrash, IconUpload } from '@tabler/icons-react';
import { useMemo } from 'react';


function WirevizBomRow({
    context,
    row,
}: {
    context: InvenTreePluginContext,
    row: any
}) {

    const partLink: string = (!!row.sub_part && !!row.pn) ? getDetailUrl(ModelType.part, row.sub_part, true) : '';

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
                {partLink ? (
                    <Anchor href={partLink} onClick={(event: any) => navigateToLink(partLink, context.navigate, event)}>{row.pn}</Anchor>
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

    const canEdit : boolean = useMemo(() => wirevizContext.context?.can_edit ?? false, [wirevizContext.context]);

    const deleteDiagram = context.forms.create({
        title: 'Remove Wireviz Diagram',
        url: apiUrl("/plugin/wireviz/delete/"),
        method: 'POST',
        fields: {
            part: {
                value: context.id,
                hidden: true,
            },
        },
        preFormContent: (
            <Alert color='red' title="Delete Diagram">
                Delete the Wireviz diagram from this part?
            </Alert>
        ),
        successMessage: 'Diagram removed',
        onFormSuccess: () => {
            // Hacky: reload the page to refresh the diagram
            window.location.reload();
        },
    });

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
        },
        successMessage: 'Diagram uploaded',
        onFormSuccess: () => {
            // Hacky: reload the page to refresh the diagram
            // TODO: Dynamically inject the new diagram into the page
            window.location.reload();
        }
    });

    return (
        <>
        {canEdit && newDiagram.modal}
        {canEdit && deleteDiagram.modal}
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
            {canEdit && (
                <Menu position='bottom-end' withArrow>
                    <Menu.Target>
                        <ActionIcon variant="transparent">
                            <IconDotsVertical />
                        </ActionIcon>
                    </Menu.Target>
                    <Menu.Dropdown>
                        <Menu.Item onClick={newDiagram.open} leftSection={<IconUpload color="green" />} >Upload New Diagram</Menu.Item>
                        {wirevizSource && <Menu.Item onClick={deleteDiagram.open} leftSection={<IconTrash color="red"/>}>Remove Diagram</Menu.Item>}
                    </Menu.Dropdown>
                </Menu>
            )}
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
            <Table striped>
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
                        <WirevizBomRow row={row} context={context}/>
                    ))}
                </Table.Tbody>
            </Table>
        </Stack>
        </Paper>
        </SimpleGrid>
        {wirevizSource && (
            <Paper shadow="lg" p="md">
                <Anchor href={wirevizSource} target="_blank">
                    <Group gap='xs'>
                        <IconFile />
                        <Text>Wireviz Source File</Text>
                    </Group>
                </Anchor>
            </Paper>
        )}
        </Stack>
        </>
    );
}


export function renderWirevizPanel(context: InvenTreePluginContext) {
    checkPluginVersion(context);
    console.log("Plugin Context:", context.context);

    return <WirevizPanel context={context} />;
}