export const apiRoot = import.meta.env.DEV ? '/api' : 'https://aukwjgzbqtsbvrhzyisi.supabase.co';

export const langnames = {
  'es': 'Spanish',
  'pt': 'Portuguese',
  'fr': 'French',
  'it': 'Italian',
  'en': 'English',
  'la': 'Latin',
  'osp': 'Old Spanish',
  'fro': 'Old French',
  'grc': 'Ancient Greek',
  'ine-pro': 'Proto-Indo-European',
  'itc-pro': 'Proto-Italic',

  'de': 'German',
  'gmw-hgm': 'High German',
  'gmw-lgm': 'Low German', 
  'goh': 'Old High German', 
  'gml': 'Middle Low German', 
  'gmh': 'German Low German', 
  'gem': 'Germanic', 
  'gmq': 'North Germanic',
  'osx': 'Old Saxon',

  'gmw-pro': 'Proto-West Germanic',
  'gem-pro': 'Proto-Germanic',
  'nl': 'Dutch',
} as Record<string, string>;