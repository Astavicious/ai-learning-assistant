import {test,expect} from '@playwright/test';

test('sample workspace keeps active question across tools and supports keyboard tabs',async({page},testInfo)=>{
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Less searching. More understanding.'})).toBeVisible();
  await page.getByRole('button',{name:'Try the sample course'}).click();
  await expect(page.getByText('5 selected',{exact:true})).toBeVisible({timeout:30000});
  await page.getByRole('textbox',{name:'Ask about your documents'}).fill('How are folds different?');
  await page.getByRole('tab',{name:'Quiz',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Put your understanding to work.'})).toBeVisible();
  await page.getByRole('tab',{name:'Ask',exact:true}).focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab',{name:'Summary',exact:true})).toBeFocused();
  await page.keyboard.press('Home');
  await expect(page.getByRole('textbox',{name:'Ask about your documents'})).toHaveValue('How are folds different?');
  if(testInfo.project.name==='mobile'){
    await page.getByRole('button',{name:'Library (5)'}).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toHaveCount(0);
  }
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:`../docs/screenshots/workspace-${testInfo.project.name}.png`,fullPage:true});
});

test('quiz scoring and Anki export consume validated API results',async({page})=>{
  // The model/API boundary is stubbed; this test makes no live model-quality claim.
  let kind='quiz';
  await page.route('**/api/study-materials',async route=>{
    if(route.request().method()!=='POST')return route.continue();
    kind=route.request().postDataJSON().kind;
    await route.fulfill({json:{id:'fixture-job',status:'queued',stage:'queued',progress:0,document_id:null,result:null,error:null}});
  });
  const citation={source_id:'fixture',document_id:'sample-Lecture-1-Pure-Functions',filename:'Lecture-1-Pure-Functions.pdf',page:1,quote:'A pure function returns the same output for the same input and has no side effects.'};
  await page.route('**/api/jobs/fixture-job',route=>route.fulfill({json:{id:'fixture-job',status:'completed',stage:'ready',progress:100,document_id:null,error:null,result:kind==='quiz'?{kind:'quiz',questions:Array.from({length:5},(_,i)=>({question:`Purity check ${i+1}`,options:['Pure','Effectful','Unknown','None'],correct_index:0,explanation:'Pure functions have no side effects.',citations:[citation]}))}:{kind:'flashcards',cards:Array.from({length:10},(_,i)=>({question:`Card ${i+1}`,answer:'No side effects.',citations:[citation]}))}}}));
  await page.goto('/');await page.getByRole('button',{name:'Try the sample course'}).click();
  await expect(page.getByText('5 selected',{exact:true})).toBeVisible();
  await page.getByRole('tab',{name:'Quiz',exact:true}).click();await page.getByRole('button',{name:'Create quiz'}).click();
  await page.getByRole('radio',{name:'Pure',exact:true}).first().check();
  await page.getByRole('button',{name:'Submit quiz'}).click();
  await expect(page.getByText('1 / 5',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:/Lecture-1-Pure-Functions.*p. 1/}).first().click();
  await expect(page.getByRole('img',{name:'PDF preview, physical page 1'}).last()).toBeVisible();
  const close=page.getByRole('button',{name:'Close Source evidence'});if(await close.isVisible())await close.click();
  await page.getByRole('tab',{name:'Flashcards',exact:true}).click();await page.getByRole('button',{name:'Create flashcards'}).click();
  await page.getByRole('button',{name:'Show answer'}).click();await expect(page.getByText('No side effects.',{exact:true})).toBeVisible();
  const downloaded=page.waitForEvent('download');await page.getByRole('button',{name:'Export for Anki'}).click();
  expect((await downloaded).suggestedFilename()).toBe('flashcards.tsv');
});
