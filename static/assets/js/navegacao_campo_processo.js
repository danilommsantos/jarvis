var form = document.getElementById("minuta-form");
if (!isAparelhoMovelIOS())
{
	if (form) 
	{
   //Script para chamar a função na ação de colar o número do processo completo no campo "Número"
	document.forms[0].numProc.onpaste = formataNumeroProcesso;
	//Navegação automática
	document.forms[0].numProc.onkeypress = function(event){navegacaoAuto(event, this.name, this.maxLength);};
	 
	//Navegação automática 
	document.forms[0].digito.onkeypress = function(event){navegacaoAuto(event, this.name, this.maxLength);}; 
	//Navegação na ação de apagar usando o backspace 
	document.forms[0].digito.onkeydown = function(event){backspace(event, this.name);};
	 
	//Navegação automática 
	document.forms[0].anoProc.onkeypress = function(event){navegacaoAuto(event, this.name, this.maxLength);}; 
	//Navegação na ação de apagar usando o backspace 
	document.forms[0].anoProc.onkeydown = function(event){backspace(event, this.name);};
	
	//Navegação automática 
	document.forms[0].justica.onkeypress = function(event){navegacaoAuto(event, this.name, this.maxLength);}; 
	//Navegação na ação de apagar usando o backspace 
	document.forms[0].justica.onkeydown = function(event){backspace(event, this.name);};
	
	//Navegação automática 
	document.forms[0].numTribunal.onkeypress = function(event){navegacaoAuto(event, this.name, this.maxLength);}; 
	//Navegação na ação de apagar usando o backspace 
	document.forms[0].numTribunal.onkeydown = function(event){backspace(event, this.name);};
	
	//Navegação na ação de apagar usando o backspace 
	document.forms[0].numVara.onkeydown = function(event){backspace(event, this.name);};
	}
}


function isAparelhoMovelIOS() {
	var indAparelhoMovelIOS = false;
	var versaoApp = navigator.appVersion.toLowerCase();
	if ( versaoApp.indexOf("iphone") != -1 
		|| versaoApp.indexOf("ipad") != -1
		|| versaoApp.indexOf("ipod") != -1 ) {
		indAparelhoMovelIOS = true;
	}
	return indAparelhoMovelIOS;
}