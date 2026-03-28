/** @format */

function pad(num, size) {
  num = num.toString();
  while (num.length < size) num = "0" + num;
  return num;
}

function get_artigo() {
  return $("#artigo").val();
}

function consultar(link) {
  link = "http://" + link + get_artigo();
  window.open(link);
}

function consultar_sumula() {
  let numero = get_artigo();
  let pagina;
  switch (true) {
    case numero <= 50:
      pagina = "1_50";
      break;
    case numero <= 100:
      pagina = "51_100";
      break;
    case numero <= 150:
      pagina = "101_150";
      break;
    case numero <= 200:
      pagina = "151_200";
      break;
    case numero <= 250:
      pagina = "201_250";
      break;
    case numero <= 300:
      pagina = "251_300";
      break;
    case numero <= 350:
      pagina = "301_350";
      break;
    case numero <= 400:
      pagina = "351_400";
      break;
    case numero <= 450:
      pagina = "401_450";
      break;
    default:
      pagina = "451_600";
      break;
  }
  let link =
    "https://www3.tst.jus.br/jurisprudencia/Sumulas_com_indice/Sumulas_Ind_" +
    pagina +
    ".html#SUM-" +
    numero;
  window.open(link);
}

function consultar_oj_sdi_1() {
  let numero = get_artigo();
  let pagina = numero - ((numero - 1) % 20);
  let tipo_ext;
  if (numero > 380) {
    tipo_ext = ".html";
  } else {
    tipo_ext = ".htm";
  }

  let link =
    "https://www3.tst.jus.br/jurisprudencia/OJ_SDI_1/n_s1_" +
    pad(pagina, 3) +
    tipo_ext +
    "#TEMA" +
    numero;
  window.open(link);
}

function consultar_oj_sdi_trans_1() {
  let link =
    "https://www3.tst.jus.br/jurisprudencia/OJ_SDI_1_Transitoria/n_transitoria.html#Tema" +
    pad(get_artigo(), 2);
  window.open(link);
}

function consultar_oj_sdi_2() {
  let numero = get_artigo();
  let pagina = numero - ((numero - 1) % 20);
  let tipo_ext = ".htm";
  let s;
  if (numero > 100) {
    s = "6";
  } else {
    s = "5";
  }

  let link =
    "https://www3.tst.jus.br/jurisprudencia/OJ_SDI_2/n_S" +
    s +
    "_" +
    pad(pagina, 2) +
    tipo_ext +
    "#tema" +
    pad(numero, 2);
  window.open(link);
}

function consultar_sdc() {
  let numero = get_artigo();
  let pagina = numero - ((numero - 1) % 20);
  let link =
    "https://www3.tst.jus.br/jurisprudencia/OJ_SDC/n_bol_" +
    pad(pagina, 2) +
    ".html#TEMA" +
    numero;
  window.open(link);
}
