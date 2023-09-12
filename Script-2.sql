select * from sys.`x$memory_by_thread_by_current_bytes`;



select * from sys.`x$memory_by_user_by_current_bytes`


select * from sys.`schema_object_overview`

select * from sys.`schema_tables_with_full_table_scans`

select
	`USR` . `RECORDID`
from
	`SYSTEMNPVRRECORDING` `SYS`
inner join `USERNPVRRECORDING` `USR` on
	`SYS` . `RECORDID` = `USR` . `RECORDID`
inner join (
	select
		`PROGRAMEXTERNALID` ,
		`PROGRAMSTARTTIME`
	from
		`USERNPVRRECORDING` `U`
	inner join `SYSTEMNPVRRECORDING` `S` on
		`U` . `RECORDID` = `S` . `RECORDID`
	where
		`U` . `USERID` = ?
		and `U` . `SERIESID` = ?
		and `U` . `USERNAME` = ? ) `TEMPDATA` on
	`SYS` . `PROGRAMEXTERNALID` = `TEMPDATA` . `PROGRAMEXTERNALID`
	and `SYS` . `PROGRAMSTARTTIME` = `TEMPDATA` . `PROGRAMSTARTTIME`
where
	`USERID` = ?
	and `SERIESID` = ?
	and `MARKEDFORDELETE` = ?
	and `USERNAME` = ?
	
	
	
use npvrbe;

select
	USR.RECORDID
from
	SYSTEMNPVRRECORDING SYS
inner join USERNPVRRECORDING USR
on
	SYS.RECORDID = USR.RECORDID
inner join (
	select
		PROGRAMEXTERNALID,
		PROGRAMSTARTTIME
	from
		USERNPVRRECORDING U
	inner join SYSTEMNPVRRECORDING S
on
		U.RECORDID = S.RECORDID
	where
		U.USERID = 1944701
		and U.SERIESID = 127310
		and U.USERNAME like '%TSPT2623279%' 
) TEMPDATA
on
	SYS.PROGRAMEXTERNALID = TEMPDATA.PROGRAMEXTERNALID
	and SYS.PROGRAMSTARTTIME = TEMPDATA.PROGRAMSTARTTIME
where
	USERID = 1944701
	and SERIESID = 127310
	and MARKEDFORDELETE = 0
	and USERNAME like '%TSPT2623279%';