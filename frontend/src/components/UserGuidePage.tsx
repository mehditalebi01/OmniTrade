import {
  Accordion, AccordionDetails, AccordionSummary, Alert, Box, Button, Chip,
  Stack, Typography,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import DescriptionIcon from '@mui/icons-material/Description';
import DownloadIcon from '@mui/icons-material/Download';
import { guideTopics } from '../userGuide';

export default function UserGuidePage() {
  return <Stack spacing={2} sx={{ maxWidth: 1000 }}>
    <Box>
      <Typography variant="h4" fontWeight={800}>How to Use OmniTrade AI</Typography>
      <Typography color="text.secondary">Select an index range to read its complete steps.</Typography>
    </Box>
    <Alert severity="warning">OmniTrade gives financial decision support. It does not execute trades and its result is not a guarantee.</Alert>
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
      <Button startIcon={<DescriptionIcon/>} variant="contained" href="/OmniTrade-AI-User-Guide.md" target="_blank">Open complete guide file</Button>
      <Button startIcon={<DownloadIcon/>} variant="outlined" href="/OmniTrade-AI-User-Guide.md" download>Download guide</Button>
    </Stack>
    <Box>
      {guideTopics.map(topic => <Accordion key={topic.range} disableGutters>
        <AccordionSummary expandIcon={<ExpandMoreIcon/>} aria-controls={`guide-${topic.range}`}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <Chip label={topic.range} color="primary"/>
            <Box>
              <Typography fontWeight={800}>{topic.title}</Typography>
              <Typography variant="body2" color="text.secondary">{topic.summary}</Typography>
            </Box>
          </Stack>
        </AccordionSummary>
        <AccordionDetails id={`guide-${topic.range}`}>
          <Stack component="ol" spacing={1} sx={{ pl: 2.5, m: 0 }}>
            {topic.steps.map(step => <li key={step}><Typography color="text.secondary">{step}</Typography></li>)}
          </Stack>
        </AccordionDetails>
      </Accordion>)}
    </Box>
    <Alert severity="info">When an option is missing, open Connections and verify the required provider. OmniTrade never replaces a failed real provider with fake data.</Alert>
  </Stack>;
}
